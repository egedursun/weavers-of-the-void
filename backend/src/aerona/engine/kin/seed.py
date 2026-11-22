from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.kin import AVENGING, LINE_ROLES
from aerona.constants.units import PERCENT
from aerona.db.tables.cycles import KinshipSystemRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin import KinGroupMemberRow, KinGroupRow, KinRoleDutyRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import DescentGroup, KinTermSystem, ResidenceRule
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.kin import KinDuty, KinGroupForm, KinMembership, KinRole
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record

R = KinRole
D = KinDuty
BASE: tuple[tuple[KinRole, KinDuty, int], ...] = (
    (R.PARENT, D.RAISE, 140),
    (R.PARENT, D.SUPPORT, 120),
    (R.PARENT, D.MOURN, 140),
    (R.PARENT, D.TEACH, 100),
    (R.CHILD, D.SUPPORT, 100),
    (R.CHILD, D.INHERIT_FROM, 140),
    (R.CHILD, D.MOURN, 140),
    (R.CHILD, D.OBEY, 80),
    (R.SIBLING, D.SUPPORT, 80),
    (R.SIBLING, D.PROTECT, 80),
    (R.SIBLING, D.MOURN, 100),
    (R.GRANDPARENT, D.RAISE, 80),
    (R.GRANDPARENT, D.TEACH, 100),
    (R.GRANDCHILD, D.SUPPORT, 60),
    (R.SIBLING_CHILD, D.SUPPORT, 40),
    (R.PARENT_IN_LAW, D.HOST, 60),
    (R.SIBLING_IN_LAW, D.HOST, 40),
    (R.CO_SPOUSE, D.SUPPORT, 60),
    (R.CHOSEN_KIN, D.SUPPORT, 100),
    (R.CHOSEN_KIN, D.RAISE, 80),
    (R.GODPARENT, D.TEACH, 80),
    (R.GODPARENT, D.RAISE, 60),
    (R.SWORN_KIN, D.PROTECT, 120),
    (R.SWORN_KIN, D.SUPPORT, 100),
)
GROUP_FORMS = {DescentGroup.LINEAGE: KinGroupForm.LINEAGE, DescentGroup.CLAN: KinGroupForm.CLAN, DescentGroup.MOIETY: KinGroupForm.MOIETY}
EXOGAMOUS = frozenset({KinGroupForm.CLAN, KinGroupForm.MOIETY})


@dataclass
class KinSeedTally:
    duties: int = 0
    groups: int = 0
    members: int = 0


def duties_for(system: KinshipSystemRow | None, values: dict[ValueAxis, int], base: int) -> dict[tuple[KinRole, KinDuty], int]:
    found = {(role, duty): clamp_int(base * weight // PERCENT, 0, PERCENT) for role, duty, weight in BASE}
    if system is not None:
        line = LINE_ROLES.get(system.descent)
        if line is not None:
            found[(line, D.RAISE)] = clamp_int(base, 0, PERCENT)
            found[(line, D.INHERIT_FROM)] = clamp_int(base, 0, PERCENT)
        if system.kin_terms is KinTermSystem.CROSS_PARALLEL:
            found[(R.COUSIN_CROSS, D.MARRY_TO)] = clamp_int(base, 0, PERCENT)
            found[(R.COUSIN_PARALLEL, D.AVOID)] = clamp_int(base // 2, 0, PERCENT)
        if system.residence in {ResidenceRule.WITH_FIRST_FAMILY, ResidenceRule.WITH_SECOND_FAMILY}:
            found[(R.PARENT_IN_LAW, D.OBEY)] = clamp_int(base, 0, PERCENT)
    honour = values.get(ValueAxis.HONOUR, 0)
    if honour > 0:
        for role in AVENGING:
            found[(role, D.AVENGE)] = clamp_int(base * honour // PERCENT, 0, PERCENT)
    family = values.get(ValueAxis.FAMILY, 0)
    for key in list(found):
        if key[1] is D.SUPPORT:
            found[key] = clamp_int(found[key] + family // 4, 0, PERCENT)
    return {key: strength for key, strength in found.items() if strength > 0}


async def peoples(ctx: TickContext) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )


async def seed_duties(ctx: TickContext, tally: KinSeedTally) -> None:
    owned = set(await ctx.session.scalars(select(KinRoleDutyRow.people_entity_id).distinct()))
    for folk in await peoples(ctx):
        if folk.id in owned or held(folk.id):
            continue
        system = await ctx.session.get(KinshipSystemRow, folk.id)
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        for (role, duty), strength in sorted(duties_for(system, values, ctx.rules.kin.founding_strength).items()):
            ctx.session.add(KinRoleDutyRow(people_entity_id=folk.id, role=role, duty=duty, strength=strength, locked=[]))
        tally.duties += 1


async def found_group(ctx: TickContext, folk_id: int, name: str, form: KinGroupForm, *, house_id: int | None = None, head_id: int | None = None) -> KinGroupRow:
    group = KinGroupRow(
        people_entity_id=folk_id,
        name=name,
        form=form,
        membership=KinMembership.DESCENT,
        exogamy=ctx.rules.kin.group_exogamy_strength if form in EXOGAMOUS else 0,
        head_node_id=head_id,
        house_entity_id=house_id,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(group)
    await ctx.session.flush()
    await record(
        ctx,
        "kin.group_founded",
        roles={IncidentRole.SUBJECT: folk_id, **({IncidentRole.LEADER: head_id} if head_id is not None else {})},
        facts={"group": name, "form": form},
    )
    return group


async def seed_houses(ctx: TickContext, tally: KinSeedTally) -> None:
    grouped = set(await ctx.session.scalars(select(KinGroupRow.house_entity_id).where(KinGroupRow.house_entity_id.is_not(None))))
    for house, profile in await ctx.session.execute(
        select(EntityRow, HouseProfileRow).join(HouseProfileRow, HouseProfileRow.house_entity_id == EntityRow.id).order_by(EntityRow.id)
    ):
        if house.id in grouped or house.status is not EntityStatus.CANON or held(house.id):
            continue
        founder = await ctx.session.get(EntityRow, profile.founder_entity_id or profile.head_entity_id or house.id)
        folk = await people_of(ctx.session, founder) if founder is not None else None
        if folk is None:
            continue
        group = await found_group(ctx, folk.id, house.name, KinGroupForm.HOUSE, house_id=house.id, head_id=profile.head_entity_id)
        for member in await ctx.session.scalars(
            select(HouseMemberRow).where(HouseMemberRow.house_entity_id == house.id).order_by(HouseMemberRow.mortal_entity_id)
        ):
            ctx.session.add(
                KinGroupMemberRow(
                    group_id=group.id, member_node_id=member.mortal_entity_id, adopted=member.by_marriage, joined_epoch=member.joined_epoch, locked=[]
                )
            )
            tally.members += 1
        tally.groups += 1


async def seed_descent(ctx: TickContext, tally: KinSeedTally) -> None:
    for folk in await peoples(ctx):
        system = await ctx.session.get(KinshipSystemRow, folk.id)
        form = GROUP_FORMS.get(system.descent_group) if system is not None else None
        if form is None or held(folk.id):
            continue
        group = await ctx.session.scalar(
            select(KinGroupRow).where(KinGroupRow.people_entity_id == folk.id, KinGroupRow.form == form).order_by(KinGroupRow.id).limit(1)
        )
        if group is None:
            group = await found_group(ctx, folk.id, folk.name, form)
            tally.groups += 1
        if group.membership is not KinMembership.DESCENT:
            continue
        members = set(await ctx.session.scalars(select(KinGroupMemberRow.member_node_id).where(KinGroupMemberRow.group_id == group.id)))
        mortals = await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
        for mortal in list(mortals):
            if mortal.id in members or held(mortal.id):
                continue
            own = await people_of(ctx.session, mortal)
            if own is not None and own.id == folk.id:
                ctx.session.add(KinGroupMemberRow(group_id=group.id, member_node_id=mortal.id, adopted=False, joined_epoch=ctx.epoch, locked=[]))
                tally.members += 1


async def seed_kin(ctx: TickContext) -> KinSeedTally:
    tally = KinSeedTally()
    await seed_duties(ctx, tally)
    await seed_houses(ctx, tally)
    await seed_descent(ctx, tally)
    await ctx.session.flush()
    return tally
