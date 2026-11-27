from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.revivals import REVIVAL_WAYS, SIGNS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import LanguageStandingRow
from aerona.db.tables.customs import RevivalRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.society_depth import DriftCauseRow, PolityLoyaltyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import CollectiveActKind, CollectiveTrigger, CrowdFeeling
from aerona.domain.enums.customs import RevivalGoal, RevivalStage, RevivalWay
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.domain.enums.society_depth import DriftCause
from aerona.domain.models.entity_stats import CultStats
from aerona.engine.body.customs import people_of
from aerona.engine.climes.crossings import road_belonging
from aerona.engine.collective.crowds import CrowdTally, spark
from aerona.engine.collective.feelings import stir_feelings
from aerona.engine.context import TickContext
from aerona.engine.lore.names import tongue_of
from aerona.engine.mind.book import clamp_value, stored_values, write_values
from aerona.engine.polity.laws import ruling_law
from aerona.engine.primitives.faith import change_religion, is_living_god, patron_node
from aerona.engine.primitives.folk import present_among, towns_of_people
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.renown.currencies import ruler_of_realm
from aerona.engine.services.community_relations import change_relation
from aerona.engine.settlement.control import build_district
from aerona.rules.registry import Rules

PRESSING = frozenset({DriftCause.RULER, DriftCause.CONQUEST, DriftCause.NEIGHBOURS})
STAGES = (RevivalStage.STEADY, RevivalStage.STRESS, RevivalStage.DISTORTION, RevivalStage.REVITALISATION, RevivalStage.NEW_STEADY)


@dataclass
class RevivalTally:
    begun: int = 0
    turned: int = 0
    settled: int = 0
    suppressed: int = 0


async def towns_of(ctx: TickContext, people_id: int) -> list[int]:
    return await towns_of_people(ctx.session, people_id)


async def pressure_on(ctx: TickContext, people_id: int) -> int:
    eased = 1 - await road_belonging(ctx.session, people_id) * ctx.rules.cosmopolitan.nativism_ease_pct / PERCENT / PERCENT
    return round(await pressed_on(ctx, people_id) * eased)


async def pressed_on(ctx: TickContext, people_id: int) -> int:
    homes = [people_id, *await towns_of(ctx, people_id)]
    since = ctx.epoch - ctx.rules.revivals.memory_epochs
    rows = await ctx.session.execute(
        select(func.sum(func.abs(DriftCauseRow.amount))).where(
            DriftCauseRow.community_entity_id.in_(homes), DriftCauseRow.cause.in_(list(PRESSING)), DriftCauseRow.epoch >= since
        )
    )
    return int(rows.scalar() or 0)


async def dominant_of(ctx: TickContext, people_id: int) -> int | None:
    towns = await towns_of(ctx, people_id)
    if not towns:
        return None
    realm = await ctx.session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id.in_(towns)).order_by(PolityMemberRow.polity_entity_id).limit(1)
    )
    if realm is None:
        return None
    ruler = await ruler_of_realm(ctx.session, realm)
    ruling = await ctx.session.get(EntityRow, ruler) if ruler is not None else None
    folk = await people_of(ctx.session, ruling) if ruling is not None else None
    return int(realm) if folk is not None and folk.id != people_id else None


def leaning_of(values: dict[ValueAxis, int], way: RevivalWay) -> float:
    return max(0.1, 1 + sum(values.get(axis, 0) for axis in REVIVAL_WAYS[way].leaning) / PERCENT)


def way_for(ctx: TickContext, values: dict[ValueAxis, int], rng_key: str) -> RevivalWay:
    ways = list(RevivalWay)
    weights = [REVIVAL_WAYS[way].weight(ctx.rules) * leaning_of(values, way) for way in ways]
    if sum(weights) <= 0:
        return RevivalWay.RESTORE
    return ctx.rng(rng_key).weighted(ways, weights)


def goal_for(ctx: TickContext, way: RevivalWay, rng_key: str) -> RevivalGoal:
    return ctx.rng(rng_key).pick(sorted(REVIVAL_WAYS[way].goals))


async def prophet_for(ctx: TickContext, people_id: int) -> int | None:
    towns = await towns_of(ctx, people_id)
    if not towns:
        return None
    here = await present_among(ctx.session, towns)
    found = await ctx.session.scalar(
        select(EntityRow.id).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )
    return int(found) if found is not None and not held(int(found)) else None


async def open_revival(ctx: TickContext, people: EntityRow, tally: RevivalTally) -> RevivalRow | None:
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
    way = way_for(ctx, values, seed_of("revival.way", people.id, ctx.epoch))
    goal = goal_for(ctx, way, seed_of("revival", people.id, ctx.epoch))
    row = RevivalRow(
        people_entity_id=people.id,
        dominant_entity_id=await dominant_of(ctx, people.id),
        way=way,
        stage=RevivalStage.STRESS,
        goal=goal,
        strength=0,
        prophet_node_id=await prophet_for(ctx, people.id) if REVIVAL_WAYS[way].founds_faith else None,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.begun += 1
    await record(
        ctx,
        "revivals.begun",
        roles={IncidentRole.ACTOR: people.id, IncidentRole.OPPONENT: row.dominant_entity_id, IncidentRole.LEADER: row.prophet_node_id},
        facts={"way": way, "goal": goal},
        steps=(StepDraft(StepAction.BEGIN, actor=people.id),),
    )
    await way_chosen(ctx, row)
    return row


async def way_chosen(ctx: TickContext, row: RevivalRow) -> None:
    await record(
        ctx,
        "revival.way_chosen",
        roles={IncidentRole.ACTOR: row.people_entity_id, IncidentRole.LEADER: row.prophet_node_id},
        facts={"way": row.way, "goal": row.goal},
    )


async def pressed_drift(ctx: TickContext, people_id: int) -> dict[ValueAxis, int]:
    homes = [people_id, *await towns_of(ctx, people_id)]
    rows = await ctx.session.execute(
        select(DriftCauseRow.axis, func.sum(DriftCauseRow.total))
        .where(DriftCauseRow.community_entity_id.in_(homes), DriftCauseRow.cause.in_(list(PRESSING)))
        .group_by(DriftCauseRow.axis)
    )
    return {axis: int(total or 0) for axis, total in rows.all()}


async def pull_values(ctx: TickContext, row: RevivalRow) -> None:
    pull = ctx.rules.revivals.value_pull_pct / PERCENT
    values = await stored_values(ctx.session, ValueHolder.CULTURE, row.people_entity_id)
    if REVIVAL_WAYS[row.way].pulls_to_ruler and row.dominant_entity_id is not None:
        ruler = await ruler_of_realm(ctx.session, row.dominant_entity_id)
        ruling = await ctx.session.get(EntityRow, ruler) if ruler is not None else None
        folk = await people_of(ctx.session, ruling) if ruling is not None else None
        target = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id) if folk is not None else {}
        shifted = {axis: clamp_value(value + (target.get(axis, value) - value) * pull) for axis, value in values.items()}
    else:
        drift = await pressed_drift(ctx, row.people_entity_id)
        shifted = {axis: clamp_value(value - drift.get(axis, 0) * pull) for axis, value in values.items()}
    if REVIVAL_WAYS[row.way].founds_faith:
        shifted[ValueAxis.PIETY] = clamp_value(shifted.get(ValueAxis.PIETY, 0) + ctx.rules.revivals.stage_gain * pull)
    await write_values(ctx.session, ValueHolder.CULTURE, row.people_entity_id, shifted)


async def revive_language(ctx: TickContext, row: RevivalRow, people: EntityRow) -> bool:
    tongue = await tongue_of(ctx.session, people)
    standing = await ctx.session.get(LanguageStandingRow, tongue.id) if tongue is not None else None
    if standing is None:
        return False
    if "prestige" not in standing.locked:
        standing.prestige = clamp_int(standing.prestige + ctx.rules.revivals.language_gain, 0, PERCENT)
    return standing.prestige >= ctx.rules.revival.language_met_at


async def expel_foreigners(ctx: TickContext, row: RevivalRow, people: EntityRow) -> bool:
    if row.dominant_entity_id is None:
        return True
    await change_relation(
        ctx,
        people.id,
        row.dominant_entity_id,
        -ctx.rules.revivals.expel_opinion,
        MemoryKind.ILL_WILL,
        note="pressed its ways on us",
        reverse_note="pushed back against our ways",
    )
    return await dominant_of(ctx, people.id) is None


async def restore_land(ctx: TickContext, row: RevivalRow, people: EntityRow) -> bool:
    realm = await dominant_of(ctx, people.id)
    if realm is None:
        return True
    for town in await towns_of(ctx, people.id):
        loyalty = await ctx.session.get(PolityLoyaltyRow, (realm, town))
        if loyalty is not None and not held(town) and "grievances" not in loyalty.locked:
            loyalty.grievances += ctx.rules.revival.land_grievance
    return False


async def restore_rule(ctx: TickContext, row: RevivalRow, people: EntityRow) -> bool:
    return await dominant_of(ctx, people.id) is None


async def restore_law(ctx: TickContext, row: RevivalRow, people: EntityRow) -> bool:
    realm = await dominant_of(ctx, people.id)
    if realm is None or await ruling_law(ctx.session, realm, LawKind.CUSTOM) is not None:
        return True
    for town in await towns_of(ctx, people.id):
        loyalty = await ctx.session.get(PolityLoyaltyRow, (realm, town))
        if loyalty is not None and not held(town) and "grievances" not in loyalty.locked:
            loyalty.grievances += ctx.rules.revival.law_grievance
    return False


async def restore_old_god(ctx: TickContext, row: RevivalRow, people: EntityRow) -> bool:
    return await restore_god(ctx, row, people)


GOAL_WORK: Mapping[RevivalGoal, Callable[[TickContext, RevivalRow, EntityRow], Awaitable[bool]]] = total(
    RevivalGoal,
    {
        RevivalGoal.REVIVE_LANGUAGE: revive_language,
        RevivalGoal.RESTORE_GOD: restore_old_god,
        RevivalGoal.EXPEL_FOREIGNERS: expel_foreigners,
        RevivalGoal.RESTORE_LAND: restore_land,
        RevivalGoal.RESTORE_RULE: restore_rule,
        RevivalGoal.RESTORE_LAW: restore_law,
    },
)


async def rule_push(session: AsyncSession, rules: Rules, people_id: int) -> float:
    found = await session.scalar(
        select(RevivalRow.strength)
        .where(RevivalRow.people_entity_id == people_id, RevivalRow.ended_epoch.is_(None), RevivalRow.goal == RevivalGoal.RESTORE_RULE)
        .order_by(RevivalRow.id)
        .limit(1)
    )
    return 0.0 if found is None else rules.revival.rule_pressure * (PERCENT + found) / (2 * PERCENT)


async def found_faith(ctx: TickContext, row: RevivalRow, people: EntityRow) -> None:
    if row.prophet_node_id is None or held(row.prophet_node_id):
        return
    founded = await ctx.session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == row.prophet_node_id, BondRow.kind == BondKind.SOURCE_OF, BondRow.state == BondState.ACTIVE).limit(1)
    )
    god = await patron_node(ctx.session, people)
    if founded is not None or god is None or not ctx.rng(seed_of("revival.faith", row.id, ctx.epoch)).chance(ctx.rules.revival.synthesis_found_pct):
        return
    towns = await towns_of(ctx, people.id)
    cult = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.CULT,
            name=f"The revival faith of {people.name}",
            body=f"A faith that rose among {people.name} round a prophet who joined their old ways and the new.",
            stats=CultStats(followers=max(1, stat_or(people, "population", 0) // 20), zeal=PERCENT * 3 // 5, influence=PERCENT // 5),
            power=1,
            world_id=people.world_id,
            location_id=towns[0] if towns else people.location_id,
            subtype="revival faith",
        ),
    )
    await connect(ctx.session, cult.id, god, BondKind.WORSHIPS, ctx.epoch, description="the god it joined to the new ways")
    await connect(ctx.session, row.prophet_node_id, cult.id, BondKind.SOURCE_OF, ctx.epoch, description="founded it")
    await record(
        ctx,
        "revival.faith_founded",
        roles={IncidentRole.LEADER: row.prophet_node_id, IncidentRole.ACTOR: people.id, IncidentRole.PRODUCT: cult.id},
        facts={"way": row.way},
    )


async def await_sign(ctx: TickContext, row: RevivalRow, people: EntityRow) -> None:
    signs = await ctx.session.scalar(
        select(SkyEventRow.id).where(SkyEventRow.world_id == people.world_id, SkyEventRow.epoch == ctx.epoch, SkyEventRow.kind.in_(list(SIGNS))).limit(1)
    )
    if signs is None:
        return
    risen = 0
    for town_id in await towns_of(ctx, people.id):
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or held(town_id):
            continue
        await stir_feelings(ctx, town_id, {CrowdFeeling.FERVOUR: ctx.rules.revival.sign_heat, CrowdFeeling.HOPE: ctx.rules.revival.sign_heat})
        if await spark(ctx, town, CollectiveTrigger.OMEN, CrowdTally(), forced=True, act=CollectiveActKind.REVOLT) is not None:
            risen += 1
    await record(ctx, "revival.sign_came", roles={IncidentRole.ACTOR: people.id}, facts={"towns": risen})


async def withdraw(ctx: TickContext, row: RevivalRow, people: EntityRow) -> None:
    towns = await towns_of(ctx, people.id)
    if towns and not held(towns[0]):
        quarter = await ctx.session.scalar(
            select(DistrictRow.id).where(DistrictRow.settlement_entity_id == towns[0], DistrictRow.kind == DistrictKind.FOREIGN_QUARTER).limit(1)
        )
        if quarter is None and await ctx.session.get(SettlementProfileRow, towns[0]) is not None:
            await build_district(ctx, towns[0], DistrictKind.FOREIGN_QUARTER, material=BuildMaterial.TIMBER, son_id=None)
            await record(ctx, "revival.withdrew", roles={IncidentRole.ACTOR: people.id, IncidentRole.PLACE: towns[0]}, facts={"way": row.way}, place=towns[0])
    if row.dominant_entity_id is not None:
        await change_relation(
            ctx,
            people.id,
            row.dominant_entity_id,
            ctx.rules.revival.withdraw_calm,
            MemoryKind.GOODWILL,
            note="left us to live apart",
            reverse_note="was left to live apart",
        )


async def follow_way(ctx: TickContext, row: RevivalRow, people: EntityRow) -> None:
    spec = REVIVAL_WAYS[row.way]
    if spec.clashes and row.dominant_entity_id is not None:
        await change_relation(
            ctx,
            people.id,
            row.dominant_entity_id,
            -ctx.rules.revival.clash_opinion,
            MemoryKind.ILL_WILL,
            note="stood against our old ways",
            reverse_note="held to its old ways against us",
        )
    if spec.founds_faith:
        await found_faith(ctx, row, people)
    if spec.awaits_sign:
        await await_sign(ctx, row, people)
    if spec.withdraws:
        await withdraw(ctx, row, people)


async def goal_met(ctx: TickContext, row: RevivalRow, people: EntityRow) -> None:
    if "stage" in row.locked:
        return
    row.stage = RevivalStage.NEW_STEADY
    if "ended_epoch" not in row.locked:
        row.ended_epoch = ctx.epoch
    await record(
        ctx,
        "revival.goal_met",
        roles={IncidentRole.ACTOR: people.id, IncidentRole.OPPONENT: row.dominant_entity_id},
        facts={"way": row.way, "goal": row.goal},
        steps=(StepDraft(StepAction.SETTLE, actor=people.id),),
    )


async def pursue(ctx: TickContext, row: RevivalRow, people: EntityRow) -> bool:
    await follow_way(ctx, row, people)
    met = await GOAL_WORK[row.goal](ctx, row, people)
    await pull_values(ctx, row)
    if met or REVIVAL_WAYS[row.way].assimilates:
        await goal_met(ctx, row, people)
        return True
    return False


async def old_god_of(ctx: TickContext, people: EntityRow) -> int | None:
    current = await patron_node(ctx.session, people)
    for god in await ctx.session.scalars(
        select(BondRow.target_node_id)
        .where(BondRow.source_node_id == people.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state != BondState.ACTIVE)
        .order_by(BondRow.id.desc())
    ):
        if god != current and await is_living_god(ctx.session, god):
            return int(god)
    return None


async def restore_god(ctx: TickContext, row: RevivalRow, people: EntityRow) -> bool:
    old = await old_god_of(ctx, people)
    if old is None or not ctx.rng(seed_of("revival.restore", row.id, ctx.epoch)).chance(ctx.rules.revivals.restore_chance):
        return False
    if await change_religion(ctx.session, people, old, ctx.epoch, "a movement brought it back to the god it once worshipped"):
        await record(
            ctx,
            "revivals.restored",
            roles={IncidentRole.ACTOR: people.id, IncidentRole.TARGET: old},
            facts={"goal": row.goal},
            steps=(StepDraft(StepAction.CONVERT, actor=people.id, target=old),),
        )
        return True
    return False


async def put_down(ctx: TickContext, row: RevivalRow, people: EntityRow, tally: RevivalTally) -> bool:
    if row.dominant_entity_id is None or row.stage not in (RevivalStage.DISTORTION, RevivalStage.REVITALISATION) or "stage" in row.locked:
        return False
    if held(row.dominant_entity_id) or not ctx.rng(seed_of("revival.suppress", row.id, ctx.epoch)).chance(ctx.rules.revivals.suppress_chance):
        return False
    row.stage = RevivalStage.SUPPRESSED
    if "ended_epoch" not in row.locked:
        row.ended_epoch = ctx.epoch
    tally.suppressed += 1
    await change_relation(
        ctx,
        people.id,
        row.dominant_entity_id,
        -2 * ctx.rules.revivals.expel_opinion,
        MemoryKind.ILL_WILL,
        note="put down our movement",
        reverse_note="had its movement put down by us",
    )
    await record(
        ctx,
        "revivals.suppressed",
        roles={IncidentRole.VICTIM: people.id, IncidentRole.ACTOR: row.dominant_entity_id},
        facts={"way": row.way, "goal": row.goal},
        steps=(StepDraft(StepAction.PUNISH, actor=row.dominant_entity_id, target=people.id),),
    )
    return True


async def advance(ctx: TickContext, row: RevivalRow, tally: RevivalTally) -> None:
    people = await ctx.session.get(EntityRow, row.people_entity_id)
    if people is None or people.status is not EntityStatus.CANON or held(people.id):
        return
    if await put_down(ctx, row, people, tally):
        return
    if row.stage is RevivalStage.REVITALISATION and await pursue(ctx, row, people):
        tally.settled += 1
        return
    if "strength" not in row.locked:
        row.strength = clamp_int(row.strength + ctx.rules.revivals.stage_gain, 0, PERCENT)
    if row.strength >= PERCENT and "stage" not in row.locked:
        row.stage = STAGES[min(len(STAGES) - 1, STAGES.index(row.stage) + 1)]
        row.strength = 0
        tally.turned += 1
        if row.stage is RevivalStage.NEW_STEADY and "ended_epoch" not in row.locked:
            row.ended_epoch = ctx.epoch
            tally.settled += 1
            await record(
                ctx,
                "revivals.settled",
                roles={IncidentRole.ACTOR: people.id},
                facts={"way": row.way, "goal": row.goal},
                steps=(StepDraft(StepAction.SETTLE, actor=people.id),),
            )


async def keep_revivals(ctx: TickContext, tally: RevivalTally) -> None:
    open_rows = {row.people_entity_id: row for row in await ctx.session.scalars(select(RevivalRow).where(RevivalRow.ended_epoch.is_(None)))}
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(people.id):
            continue
        row = open_rows.get(people.id)
        if row is None:
            if await pressure_on(ctx, people.id) >= ctx.rules.revivals.pressure_from:
                await open_revival(ctx, people, tally)
            continue
        await advance(ctx, row, tally)
    await ctx.session.flush()
