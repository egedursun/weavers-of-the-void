from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import LanguageStandingRow
from aerona.db.tables.customs import RevivalRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.society_depth import DriftCauseRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.customs import RevivalAim, RevivalGoal, RevivalStage
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.society_depth import DriftCause
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.lore.names import tongue_of
from aerona.engine.mind.book import clamp_value, stored_values, write_values
from aerona.engine.notes import note
from aerona.engine.primitives.faith import change_religion, is_living_god, patron_node
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.renown.currencies import ruler_of_realm
from aerona.engine.services.community_relations import change_relation

PRESSING = frozenset({DriftCause.RULER, DriftCause.CONQUEST, DriftCause.NEIGHBOURS})
STAGES = (RevivalStage.STEADY, RevivalStage.STRESS, RevivalStage.DISTORTION, RevivalStage.REVITALISATION, RevivalStage.NEW_STEADY)
RESTORING = (RevivalGoal.REVIVE_LANGUAGE, RevivalGoal.RESTORE_GOD, RevivalGoal.EXPEL_FOREIGNERS)


@dataclass
class RevivalTally:
    begun: int = 0
    turned: int = 0
    settled: int = 0
    suppressed: int = 0


async def towns_of(ctx: TickContext, people_id: int) -> list[int]:
    return list(await ctx.session.scalars(select(EntityRow.id).where(EntityRow.affiliated_entity_id == people_id, EntityRow.status == EntityStatus.CANON)))


async def pressure_on(ctx: TickContext, people_id: int) -> int:
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


def aim_for(ctx: TickContext, values: dict[ValueAxis, int]) -> RevivalAim:
    table = ctx.rules.revivals
    if values.get(ValueAxis.TRADITION, 0) >= table.restore_from:
        return RevivalAim.RESTORE
    if values.get(ValueAxis.XENOPHILIA, 0) >= table.adopt_from:
        return RevivalAim.ADOPT
    return RevivalAim.SYNTHESISE


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
    aim = aim_for(ctx, values)
    rng = ctx.rng(seed_of("revival", people.id, ctx.epoch))
    goal = rng.pick(list(RESTORING)) if aim is RevivalAim.RESTORE else RevivalGoal.ADOPT_WAYS if aim is RevivalAim.ADOPT else RevivalGoal.RESTORE_GOD
    row = RevivalRow(
        people_entity_id=people.id,
        dominant_entity_id=await dominant_of(ctx, people.id),
        aim=aim,
        stage=RevivalStage.STRESS,
        goal=goal,
        strength=0,
        prophet_node_id=await prophet_for(ctx, people.id) if aim is RevivalAim.SYNTHESISE else None,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.begun += 1
    await note(ctx, f"Pressed by others, the {people.name} began a movement to {goal.value.replace('_', ' ')}.", key="revivals.begun", ids=[people.id])
    return row


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
    if row.aim is RevivalAim.ADOPT and row.dominant_entity_id is not None:
        ruler = await ruler_of_realm(ctx.session, row.dominant_entity_id)
        ruling = await ctx.session.get(EntityRow, ruler) if ruler is not None else None
        folk = await people_of(ctx.session, ruling) if ruling is not None else None
        target = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id) if folk is not None else {}
        shifted = {axis: clamp_value(value + (target.get(axis, value) - value) * pull) for axis, value in values.items()}
    else:
        drift = await pressed_drift(ctx, row.people_entity_id)
        shifted = {axis: clamp_value(value - drift.get(axis, 0) * pull) for axis, value in values.items()}
    if row.aim is RevivalAim.SYNTHESISE:
        shifted[ValueAxis.PIETY] = clamp_value(shifted.get(ValueAxis.PIETY, 0) + ctx.rules.revivals.stage_gain * pull)
    await write_values(ctx.session, ValueHolder.CULTURE, row.people_entity_id, shifted)


async def pursue(ctx: TickContext, row: RevivalRow, people: EntityRow) -> None:
    table = ctx.rules.revivals
    if row.goal is RevivalGoal.REVIVE_LANGUAGE:
        tongue = await tongue_of(ctx.session, people)
        standing = await ctx.session.get(LanguageStandingRow, tongue.id) if tongue is not None else None
        if standing is not None and "prestige" not in standing.locked:
            standing.prestige = clamp_int(standing.prestige + table.language_gain, 0, PERCENT)
    elif row.goal is RevivalGoal.EXPEL_FOREIGNERS and row.dominant_entity_id is not None:
        await change_relation(ctx, people.id, row.dominant_entity_id, -table.expel_opinion, MemoryKind.ILL_WILL, note="pressed its ways on us")
    elif row.goal is RevivalGoal.RESTORE_GOD:
        await restore_god(ctx, row, people)
    await pull_values(ctx, row)


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


async def restore_god(ctx: TickContext, row: RevivalRow, people: EntityRow) -> None:
    old = await old_god_of(ctx, people)
    if old is None or not ctx.rng(seed_of("revival.restore", row.id, ctx.epoch)).chance(ctx.rules.revivals.restore_chance):
        return
    if await change_religion(ctx.session, people, old, ctx.epoch, "a movement brought it back to the god of its ancestors"):
        await note(ctx, f"The movement of the {people.name} brought them back to their old god.", key="revivals.restored", ids=[people.id])


async def put_down(ctx: TickContext, row: RevivalRow, people: EntityRow, tally: RevivalTally) -> bool:
    if row.dominant_entity_id is None or row.stage not in (RevivalStage.DISTORTION, RevivalStage.REVITALISATION) or "stage" in row.locked:
        return False
    if held(row.dominant_entity_id) or not ctx.rng(seed_of("revival.suppress", row.id, ctx.epoch)).chance(ctx.rules.revivals.suppress_chance):
        return False
    row.stage = RevivalStage.SUPPRESSED
    if "ended_epoch" not in row.locked:
        row.ended_epoch = ctx.epoch
    tally.suppressed += 1
    await change_relation(ctx, people.id, row.dominant_entity_id, -2 * ctx.rules.revivals.expel_opinion, MemoryKind.ILL_WILL, note="put down our movement")
    realm = await ctx.session.get(EntityRow, row.dominant_entity_id)
    await note(
        ctx,
        f"The movement of the {people.name} was put down by {realm.name if realm is not None else 'those who pressed on them'}.",
        key="revivals.suppressed",
        ids=[people.id, row.dominant_entity_id],
    )
    return True


async def advance(ctx: TickContext, row: RevivalRow, tally: RevivalTally) -> None:
    people = await ctx.session.get(EntityRow, row.people_entity_id)
    if people is None or people.status is not EntityStatus.CANON or held(people.id):
        return
    if await put_down(ctx, row, people, tally):
        return
    if row.stage is RevivalStage.REVITALISATION:
        await pursue(ctx, row, people)
    if "strength" not in row.locked:
        row.strength = clamp_int(row.strength + ctx.rules.revivals.stage_gain, 0, PERCENT)
    if row.strength >= PERCENT and "stage" not in row.locked:
        row.stage = STAGES[min(len(STAGES) - 1, STAGES.index(row.stage) + 1)]
        row.strength = 0
        tally.turned += 1
        if row.stage is RevivalStage.NEW_STEADY and "ended_epoch" not in row.locked:
            row.ended_epoch = ctx.epoch
            tally.settled += 1
            await note(ctx, f"The movement of the {people.name} settled into a new way of life.", key="revivals.settled", ids=[people.id])


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
