from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import HEAD_PARTS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import ConditionRow, InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import ConditionKind, HarmCause, NerveDamage
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.conditions import condition_of, gain_condition
from aerona.engine.body.state import refresh
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat
from aerona.engine.structures.readers import working

DECLINE = ConditionKind.COGNITIVE_DECLINE
SEVERITY_MAX = 5
CARERS = (StructureKind.HOSPITAL, StructureKind.APOTHECARY, StructureKind.ASYLUM)


@dataclass
class DeclineTally:
    onset: int = 0
    worsened: int = 0
    forgotten: int = 0


async def decline_of(session: AsyncSession, mortal_id: int) -> ConditionRow | None:
    statement = select(ConditionRow).where(ConditionRow.bearer_node_id == mortal_id, ConditionRow.kind == DECLINE, ConditionRow.ended_epoch.is_(None))
    return await session.scalar(statement.limit(1))


async def decline_severity(session: AsyncSession, mortal_id: int) -> int:
    row = await decline_of(session, mortal_id)
    return row.severity if row is not None else 0


async def too_forgetful(session: AsyncSession, mortal_id: int, block: int) -> bool:
    return await decline_severity(session, mortal_id) >= block


async def head_struck(session: AsyncSession, mortal_id: int) -> bool:
    statement = select(InjuryRow.id).where(InjuryRow.bearer_node_id == mortal_id, InjuryRow.part.in_(list(HEAD_PARTS)), InjuryRow.nerve != NerveDamage.NONE)
    return await session.scalar(statement.limit(1)) is not None


async def cared_for(session: AsyncSession, place_id: int | None) -> bool:
    return place_id is not None and bool(await working(session, CARERS, host_id=place_id))


async def onset_chance(ctx: TickContext, mortal: EntityRow) -> float:
    table = ctx.rules.decline
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    education = profile.education if profile is not None else 0
    chance = table.chance_pct * (1 - education / PERCENT * table.reserve_pct / PERCENT)
    if await head_struck(ctx.session, mortal.id):
        chance *= table.head_pct / PERCENT
    if await cared_for(ctx.session, mortal.location_id):
        chance *= table.care_pct / PERCENT
    return max(0.0, chance)


async def forget(ctx: TickContext, mortal_id: int, severity: int) -> int:
    fade = ctx.rules.decline.memory_fade * severity
    faded = 0
    for row in await ctx.session.scalars(
        select(MemoryRow).where(MemoryRow.holder_node_id == mortal_id, MemoryRow.magnitude != 0).order_by(MemoryRow.epoch, MemoryRow.id)
    ):
        step = min(abs(row.magnitude), fade)
        row.magnitude += -step if row.magnitude > 0 else step
        faded += 1
    return faded


async def run_decline(ctx: TickContext) -> DeclineTally:
    table = ctx.rules.decline
    tally = DeclineTally()
    mortals = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for mortal in list(mortals):
        age, lifespan = stat(mortal, "age"), stat(mortal, "lifespan")
        if held(mortal.id) or age is None or not lifespan or age * PERCENT < lifespan * table.onset_pct:
            continue
        row = await condition_of(ctx, mortal.id, DECLINE)
        if row is None:
            if await gain_condition(ctx, mortal, DECLINE, HarmCause.AGE, chance=await onset_chance(ctx, mortal)) is not None:
                tally.onset += 1
            continue
        progress = table.progress_pct * (table.care_pct / PERCENT if await cared_for(ctx.session, mortal.location_id) else 1.0)
        if row.severity < SEVERITY_MAX and ctx.rng(f"decline.{mortal.id}.{ctx.epoch}").chance(progress):
            row.severity += 1
            await refresh(ctx.session, ctx.rules, mortal, ctx.epoch)
            tally.worsened += 1
        tally.forgotten += await forget(ctx, mortal.id, row.severity)
    return tally


def failing_part(severity: int, senile: int) -> int:
    return -round_half_up(senile * severity / SEVERITY_MAX)
