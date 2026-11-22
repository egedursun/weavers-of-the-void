import time
from collections.abc import Callable
from dataclasses import dataclass, replace

from sqlalchemy import delete, event, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from aerona.catalog.life.prehistory import DERIVE_PREHISTORY_KINDS
from aerona.catalog.prehistory import COARSE_PHASES, PREHISTORY_GROWTH, PREHISTORY_PHASES, SIMULATED_KINDS
from aerona.core.errors import AeronaError, NotFoundError
from aerona.core.random import SeededRandom
from aerona.db.session import Database, Steps
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.prehistory import PrehistoryRow
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.prehistory import PrehistoryKind, PrehistoryState
from aerona.engine.context import Publisher, TickContext, TickEnvironment
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.phase import Phase
from aerona.engine.pipeline import TICK_ORDER, TRANSITION_ORDER, EnginePhaseError, current_environment
from aerona.engine.prehistory import digest
from aerona.engine.prehistory.rewind import Touched, epoch_points, follow_touched, mapped, rewind
from aerona.engine.primitives.manual import silent
from aerona.engine.stats import TickStats
from aerona.rules.registry import Rules

LIVING_PHASES = frozenset({"world_lives"})
SEED_CEILING = 2**62


@dataclass
class PrehistorySummary:
    world_id: int
    rounds: int = 0
    events: int = 0
    worlds_made: int = 0
    state: PrehistoryState = PrehistoryState.PLANNED


def round_seed(world_seed: int, world_id: int, number: int) -> int:
    return SeededRandom.for_epoch(world_seed, number, f"prehistory.{world_id}").integer(1, SEED_CEILING)


def round_phases(number: int, resolution: int) -> list[Phase]:
    return [phase for phase in TICK_ORDER if phase.name in PREHISTORY_PHASES and (phase.name not in COARSE_PHASES or number % resolution == 0)]


def growth_phases(kind: PrehistoryKind) -> list[Phase]:
    wanted = PREHISTORY_GROWTH | (LIVING_PHASES if kind is PrehistoryKind.LIVING else frozenset())
    return [phase for phase in TRANSITION_ORDER if phase.name in wanted]


async def own_nodes(session: AsyncSession, world_id: int) -> set[int]:
    own = {world_id, *await session.scalars(select(EntityRow.id).where(EntityRow.world_id == world_id))}
    return own | set(await session.scalars(select(ForeignGodRow.id).where(ForeignGodRow.world_id == world_id)))


def follow_inside(world_id: int, inside: set[int]) -> Callable[..., None]:
    def follow(sync: Session, *_: object) -> None:
        for row in sync.new:
            if isinstance(row, EntityRow | ForeignGodRow) and row.world_id == world_id and row.id is not None:
                inside.add(row.id)

    return follow


async def clear_points(session: AsyncSession, epoch: int, inside: set[int]) -> int:
    cleared = 0
    own = sorted(inside)
    for table, epoch_column, nodes in epoch_points():
        touching = or_(*(table.c[name].in_(own) for name in nodes))
        result = await session.execute(delete(mapped(table)).where(table.c[epoch_column] == epoch, touching))
        cleared += int(getattr(result, "rowcount", 0) or 0)
    return cleared


async def run_steps(steps: Steps, environment: TickEnvironment, phases: list[Phase], inside: set[int]) -> None:
    for phase in phases:
        try:
            async with steps.step() as session:
                await run_guarded(phase, TickContext(environment, session, phase.name), inside=inside)
        except AeronaError:
            raise
        except Exception as error:
            raise EnginePhaseError(phase.name, error) from error


Plan = tuple[int, PrehistoryKind, int]
Environments = tuple[TickEnvironment, TickEnvironment]


async def run_round(steps: Steps, plan: Plan, number: int, environments: Environments, inside: set[int]) -> None:
    world_id, kind, resolution = plan
    tick, growth = environments
    seed = round_seed(tick.world_seed, world_id, number)
    await run_steps(steps, replace(tick, epoch=tick.epoch + number, world_seed=seed, stats=TickStats()), round_phases(number, resolution), inside)
    await run_steps(steps, replace(growth, epoch=growth.epoch + number, world_seed=seed, stats=TickStats()), growth_phases(kind), inside)


async def next_round(steps: Steps, world_id: int, tick: TickEnvironment) -> tuple[int, int, Plan] | bool:
    async with steps.step() as session:
        ctx = TickContext(tick, session, "prehistory")
        row = await session.get(PrehistoryRow, world_id)
        if row is None or row.state is not PrehistoryState.RUNNING:
            return False
        if row.rounds_done >= row.epochs:
            return True
        return await digest.last_incident_id(ctx), row.rounds_done, (row.world_id, row.kind, row.resolution)


async def close_round(steps: Steps, world_id: int, tick: TickEnvironment, *, since: int, number: int, elapsed: float) -> int:
    async with steps.step() as session:
        row = await session.get(PrehistoryRow, world_id)
        if row is None:
            return 0
        kept = await digest.keep_round(TickContext(tick, session, "prehistory"), row, since, number)
        row.rounds_done = number + 1
        row.seconds += round(elapsed)
        row.slow_rounds += 1 if elapsed > tick.rules.engine_budget.prehistory_seconds_per_epoch else 0
        return kept


async def simulate_rounds(database: Database, world_id: int, rules: Rules | None, publish: Publisher, summary: PrehistorySummary) -> bool:
    tick = await current_environment(database, publish, rules, phase=EpochPhase.ENGINE)
    growth = await current_environment(database, publish, rules, phase=EpochPhase.TRANSITION)
    async with database.steps() as steps:
        async with steps.step() as session:
            inside = await own_nodes(session, world_id)
        follow = follow_inside(world_id, inside)
        touched: Touched = {}
        record = follow_touched(touched)
        event.listen(steps.session.sync_session, "after_flush", follow)
        event.listen(steps.session.sync_session, "after_flush", record)
        last: int | None = None
        try:
            while True:
                found = await next_round(steps, world_id, tick)
                if isinstance(found, bool):
                    return found
                since, number, plan = found
                last = tick.epoch + number
                started = time.perf_counter()
                if number:
                    async with steps.step() as session:
                        await clear_points(session, tick.epoch, inside)
                await run_round(steps, plan, number, (tick, growth), inside)
                summary.events += await close_round(steps, world_id, tick, since=since, number=number, elapsed=time.perf_counter() - started)
                summary.rounds += 1
        finally:
            event.remove(steps.session.sync_session, "after_flush", follow)
            event.remove(steps.session.sync_session, "after_flush", record)
            if last is not None:
                async with steps.step() as session:
                    await rewind(session, tick.epoch, last, inside, touched)


async def prepare(database: Database, world_id: int, rules: Rules | None, publish: Publisher, summary: PrehistorySummary) -> int | None:
    async with database.write() as session:
        ctx = TickContext(await current_environment(database, publish, rules, phase=EpochPhase.ENGINE), session, "prehistory")
        row = await session.get(PrehistoryRow, world_id)
        world = await session.get(WorldRow, world_id)
        if row is None or world is None:
            raise NotFoundError("That world has no prehistory to run.")
        if row.state is PrehistoryState.DONE:
            summary.state = row.state
            return None
        row.state = PrehistoryState.RUNNING
        tally = digest.DigestTally()
        twin: int | None = None
        if row.kind is PrehistoryKind.MIRRORED and row.source_world_id is None and world.mirror_twin_id is None:
            made = await digest.make_twin(ctx, world, tally)
            await digest.prehistory_of(ctx, made, row.epochs, row.resolution)
            twin = made.id
        if row.kind is PrehistoryKind.VOYAGE and row.source_world_id is None and world.parent_world_id is None:
            await digest.make_lost_origin(ctx, row, world, tally)
        summary.worlds_made += tally.worlds_made
        return twin


async def derive(database: Database, world_id: int, rules: Rules | None, publish: Publisher, summary: PrehistorySummary) -> None:
    async with database.write() as session:
        ctx = TickContext(await current_environment(database, publish, rules, phase=EpochPhase.ENGINE), session, "prehistory")
        row = await session.get(PrehistoryRow, world_id)
        world = await session.get(WorldRow, world_id)
        if row is None or world is None or row.state is not PrehistoryState.RUNNING:
            return
        god = world.creator_son_id or world.patron_son_id
        if row.kind in DERIVE_PREHISTORY_KINDS:
            summary.events += await digest.deeds_of(ctx, row, god)
        elif row.kind is PrehistoryKind.SOULS:
            summary.events += await digest.souls_of(ctx, row, world)
        elif row.kind is PrehistoryKind.DREAMT:
            summary.events += await digest.dreams_of(ctx, row, world)
        elif row.kind is PrehistoryKind.MIRRORED:
            summary.events += await digest.mirror_of(ctx, row, world)
        elif row.kind is PrehistoryKind.VOYAGE:
            summary.events += await digest.borrowed_from(ctx, row, row.source_world_id or world.parent_world_id)
        elif row.kind is PrehistoryKind.PHENOMENON:
            summary.events += await digest.borrowed_from(ctx, row, row.source_world_id)
        await digest.prune_digest(ctx, world_id, ctx.rules.prehistory.digest_size)
        row.state = PrehistoryState.DONE
        summary.state = row.state


async def run_prehistory(database: Database, world_id: int, *, rules: Rules | None = None, publish: Publisher = silent) -> PrehistorySummary:
    summary = PrehistorySummary(world_id)
    twin = await prepare(database, world_id, rules, publish, summary)
    if summary.state is PrehistoryState.DONE:
        return summary
    if twin is not None:
        await run_prehistory(database, twin, rules=rules, publish=publish)
    async with database.read() as session:
        row = await session.get(PrehistoryRow, world_id)
        simulated = row is not None and row.kind in SIMULATED_KINDS
    if simulated and not await simulate_rounds(database, world_id, rules, publish, summary):
        async with database.read() as session:
            row = await session.get(PrehistoryRow, world_id)
            summary.state = row.state if row is not None else PrehistoryState.ABORTED
        return summary
    await derive(database, world_id, rules, publish, summary)
    return summary


async def born_prehistories(database: Database, since_epoch: int, *, rules: Rules | None = None, publish: Publisher = silent) -> int:
    async with database.write() as session:
        ctx = TickContext(await current_environment(database, publish, rules, phase=EpochPhase.ENGINE), session, "prehistory")
        epochs = ctx.rules.prehistory.son_world_epochs
        planned = select(PrehistoryRow.world_id)
        born = (
            list(
                await session.scalars(
                    select(WorldRow)
                    .where(WorldRow.created_epoch >= since_epoch, WorldRow.creator_son_id.is_not(None), WorldRow.id.not_in(planned))
                    .order_by(WorldRow.id)
                )
            )
            if epochs
            else []
        )
        for world in born:
            row = await digest.prehistory_of(ctx, world, epochs, ctx.rules.prehistory.resolution)
            row.epochs = epochs
        waiting = select(PrehistoryRow.world_id).where(PrehistoryRow.state == PrehistoryState.PLANNED, PrehistoryRow.epochs > 0)
        ids = list(await session.scalars(waiting.order_by(PrehistoryRow.world_id)))
    for world_id in ids:
        await run_prehistory(database, world_id, rules=rules, publish=publish)
    return len(ids)
