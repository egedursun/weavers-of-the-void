from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.kin import RAISE_ORDER
from aerona.catalog.life_traits import LIFE_STAGE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow
from aerona.db.tables.kin import KinRoleDutyRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.thin_sections import RelationComponentRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.kin import KinDuty, KinRole
from aerona.domain.enums.life_traits import LifeStageTrait
from aerona.domain.enums.mind import MemoryKind, RelationComponent, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import shift_points
from aerona.engine.kin.roles import kin_by_role
from aerona.engine.mind.book import stored_values
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.kin import parents_of, sworn_kin_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

YOUNG = having(LIFE_STAGE_TRAITS, LifeStageTrait.DUTIES_YOUNG)
TEN = 10


@dataclass
class KinTally:
    helped: int = 0
    breached: int = 0
    fostered: int = 0
    mourned: int = 0
    avenged: int = 0
    closeness: int = 0


type Duties = dict[int, dict[tuple[KinRole, KinDuty], int]]


async def duties_by_people(ctx: TickContext) -> Duties:
    found: Duties = {}
    for row in await ctx.session.scalars(select(KinRoleDutyRow).order_by(KinRoleDutyRow.people_entity_id, KinRoleDutyRow.role, KinRoleDutyRow.duty)):
        found.setdefault(row.people_entity_id, {})[(row.role, row.duty)] = row.strength
    return found


async def living(ctx: TickContext, node_id: int) -> tuple[EntityRow, MortalProfileRow] | None:
    entity = await ctx.session.get(EntityRow, node_id)
    profile = await ctx.session.get(MortalProfileRow, node_id)
    if entity is None or profile is None or entity.status is not EntityStatus.CANON or held(node_id):
        return None
    return entity, profile


async def canon_mortals(ctx: TickContext) -> list[tuple[EntityRow, MortalProfileRow]]:
    rows = await ctx.session.execute(
        select(EntityRow, MortalProfileRow)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [(entity, profile) for entity, profile in rows if not held(entity.id)]


def bound(duties: dict[tuple[KinRole, KinDuty], int], duty: KinDuty, floor: int) -> list[tuple[KinRole, int]]:
    return sorted(((role, strength) for (role, kind), strength in duties.items() if kind is duty and strength >= floor), key=lambda pair: (-pair[1], pair[0]))


async def refuses(ctx: TickContext, giver_id: int, strength: int) -> bool:
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, giver_id)
    care = values.get(ValueAxis.FAMILY, 0) + values.get(ValueAxis.MERCY, 0)
    return care + strength < 0


async def help_in_need(ctx: TickContext, duties: Duties, tally: KinTally) -> None:
    table = ctx.rules.kin
    for needy, profile in await canon_mortals(ctx):
        if profile.wealth >= table.need_wealth:
            continue
        folk = await people_of(ctx.session, needy)
        owed = duties.get(folk.id, {}) if folk is not None else {}
        for role, strength in bound(owed, KinDuty.SUPPORT, table.duty_floor):
            given = False
            for giver_id in await kin_by_role(ctx.session, needy.id, role):
                found = await living(ctx, giver_id)
                if found is None:
                    continue
                giver, giver_profile = found
                if giver_profile.wealth < table.need_wealth * 2:
                    continue
                if await refuses(ctx, giver.id, strength):
                    await breach(ctx, giver, needy, role, KinDuty.SUPPORT)
                    tally.breached += 1
                    continue
                share = round_half_up(giver_profile.wealth * table.help_share_pct * strength / (PERCENT * PERCENT))
                if share <= 0:
                    continue
                with explaining():
                    term("kin.help_share_pct", share, source_node_id=giver.id)
                    await shift_points(ctx.session, giver, -share)
                    await shift_points(ctx.session, needy, share)
                await remember(ctx.session, ctx.rules, holder_id=needy.id, subject_id=giver.id, kind=MemoryKind.GIFTED_ME, magnitude=share, epoch=ctx.epoch)
                await record(
                    ctx,
                    "kin.duty_kept",
                    roles={IncidentRole.ACTOR: giver.id, IncidentRole.TARGET: needy.id},
                    facts={"duty": KinDuty.SUPPORT, "role": role},
                    place=needy.location_id,
                )
                tally.helped += 1
                given = True
                break
            if given:
                break
        else:
            await sworn_aid(ctx, needy, tally)


async def sworn_answers(ctx: TickContext, kin_id: int, owed_id: int, key: str) -> bool:
    return ctx.rng(f"kin.sworn.{key}.{kin_id}.{owed_id}.{ctx.epoch}").chance(ctx.rules.relations.sworn_kin_duty)


async def sworn_aid(ctx: TickContext, needy: EntityRow, tally: KinTally) -> None:
    table = ctx.rules.kin
    for kin_id in await sworn_kin_of(ctx.session, needy.id):
        found = await living(ctx, kin_id)
        if found is None or found[1].wealth < table.need_wealth * 2 or not await sworn_answers(ctx, kin_id, needy.id, "aid"):
            continue
        giver, giver_profile = found
        share = round_half_up(giver_profile.wealth * table.help_share_pct * ctx.rules.relations.sworn_kin_duty / (PERCENT * PERCENT))
        if share <= 0:
            continue
        with explaining():
            term("relations.sworn_kin_duty", share, source_node_id=giver.id)
            await shift_points(ctx.session, giver, -share)
            await shift_points(ctx.session, needy, share)
        await remember(ctx.session, ctx.rules, holder_id=needy.id, subject_id=giver.id, kind=MemoryKind.GIFTED_ME, magnitude=share, epoch=ctx.epoch)
        await record(
            ctx, "relation.sworn_aid", roles={IncidentRole.ACTOR: giver.id, IncidentRole.TARGET: needy.id}, facts={"share": share}, place=needy.location_id
        )
        tally.helped += 1
        return


async def breach(ctx: TickContext, actor: EntityRow, owed: EntityRow, role: KinRole, duty: KinDuty) -> None:
    profile = await ctx.session.get(MortalProfileRow, actor.id)
    shame = ctx.rules.kin.breach_shame
    if profile is not None and "honour" not in (profile.locked or []) and shame:
        with explaining():
            term("kin.breach_shame", -shame, source_node_id=owed.id)
            profile.honour = clamp_int(profile.honour - shame, 0, PERCENT)
    await remember(ctx.session, ctx.rules, holder_id=owed.id, subject_id=actor.id, kind=MemoryKind.BETRAYED_ME, magnitude=shame, epoch=ctx.epoch)
    await record(
        ctx,
        "kin.duty_breached",
        roles={IncidentRole.ACTOR: actor.id, IncidentRole.TARGET: owed.id},
        facts={"duty": duty, "role": role},
        place=owed.location_id,
    )


async def household_of(ctx: TickContext, node_id: int) -> HouseholdMemberRow | None:
    return await ctx.session.get(HouseholdMemberRow, node_id)


async def foster_orphans(ctx: TickContext, duties: Duties, tally: KinTally) -> None:
    table = ctx.rules.kin
    for child, profile in await canon_mortals(ctx):
        if profile.life_stage not in YOUNG or await household_of(ctx, child.id) is not None:
            continue
        parents = await parents_of(ctx.session, child.id)
        if [parent for parent in parents if await living(ctx, parent) is not None]:
            continue
        folk = await people_of(ctx.session, child)
        owed = duties.get(folk.id, {}) if folk is not None else {}
        ranked = sorted(
            RAISE_ORDER, key=lambda role: (-owed.get((role, KinDuty.RAISE), 0), RAISE_ORDER.index(role) if role in RAISE_ORDER else len(RAISE_ORDER))
        )
        for role in ranked:
            if owed.get((role, KinDuty.RAISE), 0) < table.duty_floor:
                continue
            home = None
            for keeper_id in await kin_by_role(ctx.session, child.id, role):
                if await living(ctx, keeper_id) is not None and (home := await household_of(ctx, keeper_id)) is not None:
                    break
                home = None
            if home is None:
                continue
            ctx.session.add(
                HouseholdMemberRow(
                    member_node_id=child.id, household_id=home.household_id, role=HouseholdRole.WARD, cares_for_node_id=None, joined_epoch=ctx.epoch
                )
            )
            await connect(ctx.session, child.id, home.member_node_id, BondKind.FOSTERED_BY, ctx.epoch, description="raised by kin")
            await record(
                ctx,
                "kin.duty_kept",
                roles={IncidentRole.ACTOR: home.member_node_id, IncidentRole.TARGET: child.id},
                facts={"duty": KinDuty.RAISE, "role": role},
                place=child.location_id,
            )
            tally.fostered += 1
            break


async def fresh_dead(ctx: TickContext) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.DEAD, EntityRow.end_epoch >= ctx.epoch - 1)
            .order_by(EntityRow.id)
        )
    )


async def mourn_and_avenge(ctx: TickContext, duties: Duties, tally: KinTally) -> None:
    table = ctx.rules.kin
    for dead in await fresh_dead(ctx):
        folk = await people_of(ctx.session, dead)
        owed = duties.get(folk.id, {}) if folk is not None else {}
        avengers = 0
        for role, strength in bound(owed, KinDuty.MOURN, table.duty_floor):
            for kin_id in await kin_by_role(ctx.session, dead.id, role):
                found = await living(ctx, kin_id)
                if found is None:
                    continue
                _, profile = found
                grief = round_half_up(table.mourn_mood * strength / PERCENT)
                if grief and "mood_score" not in (profile.locked or []):
                    with explaining():
                        term("kin.mourn_mood", -grief, source_node_id=dead.id)
                        profile.mood_score = clamp_int(profile.mood_score - grief, -PERCENT, PERCENT)
                    tally.mourned += 1
        for role, _strength in bound(owed, KinDuty.AVENGE, table.duty_floor):
            avengers += len([kin_id for kin_id in await kin_by_role(ctx.session, dead.id, role) if await living(ctx, kin_id) is not None])
        for kin_id in await sworn_kin_of(ctx.session, dead.id):
            avengers += await living(ctx, kin_id) is not None and await sworn_answers(ctx, kin_id, dead.id, "avenge")
        if avengers and folk is not None:
            await avenge(ctx, dead, folk.id, avengers, tally)


async def avenge(ctx: TickContext, dead: EntityRow, folk_id: int, avengers: int, tally: KinTally) -> None:
    killers = await ctx.session.scalars(
        select(BondRow.source_node_id)
        .where(BondRow.kind == BondKind.KILLED, BondRow.target_node_id == dead.id, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id)
    )
    for killer_id in list(killers):
        killer = await ctx.session.get(EntityRow, killer_id)
        their = await people_of(ctx.session, killer) if killer is not None else None
        if their is None or their.id == folk_id or held(their.id, folk_id):
            continue
        first, second = sorted((their.id, folk_id))
        relation = await ctx.session.get(CommunityRelationRow, (first, second))
        if relation is None:
            relation = CommunityRelationRow(entity_a_id=first, entity_b_id=second, value=0)
            ctx.session.add(relation)
        loss = ctx.rules.kin.avenge_feud * avengers
        with explaining():
            term("kin.avenge_feud", -loss, source_node_id=dead.id)
            relation.value = clamp_int(relation.value - loss, -PERCENT, PERCENT)
        if relation.value <= -PERCENT // 2 and relation.blood_feud_since_epoch is None:
            relation.blood_feud_since_epoch = ctx.epoch
        await record(
            ctx,
            "kin.duty_kept",
            roles={IncidentRole.ACTOR: folk_id, IncidentRole.TARGET: killer_id},
            facts={"duty": KinDuty.AVENGE, "role": KinRole.SIBLING},
        )
        tally.avenged += 1


async def keep_closeness(ctx: TickContext, duties: Duties, tally: KinTally) -> None:
    table = ctx.rules.kin
    for mortal, _profile in await canon_mortals(ctx):
        folk = await people_of(ctx.session, mortal)
        owed = duties.get(folk.id, {}) if folk is not None else {}
        for duty, sign in ((KinDuty.JOKE_WITH, 1), (KinDuty.AVOID, -1)):
            for role, strength in bound(owed, duty, table.duty_floor):
                for kin_id in await kin_by_role(ctx.session, mortal.id, role):
                    if kin_id < mortal.id or held(kin_id):
                        continue
                    component = await ctx.session.get(RelationComponentRow, (mortal.id, kin_id, RelationComponent.KINSHIP))
                    if component is None:
                        component = RelationComponentRow(entity_a_id=mortal.id, entity_b_id=kin_id, component=RelationComponent.KINSHIP, value=0, locked=[])
                        ctx.session.add(component)
                    if "value" in (component.locked or []):
                        continue
                    target = sign * strength
                    step = round_half_up((target - component.value) / TEN)
                    if step:
                        component.value = clamp_int(component.value + step, -PERCENT, PERCENT)
                        component.updated_epoch = ctx.epoch
                        tally.closeness += 1


async def keep_duties(ctx: TickContext, tally: KinTally) -> None:
    duties = await duties_by_people(ctx)
    if not duties:
        return
    await help_in_need(ctx, duties, tally)
    await foster_orphans(ctx, duties, tally)
    await mourn_and_avenge(ctx, duties, tally)
    await keep_closeness(ctx, duties, tally)
