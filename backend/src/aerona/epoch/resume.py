from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.record_context import acting
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.epochs import EpochRunRow
from aerona.db.tables.routes import HorizonIntuitionRow
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.travel import HorizonStatus
from aerona.epoch.state import plan_steps, require_run, run_of


@dataclass(frozen=True)
class HalfEpoch:
    epoch: int
    phase: int
    started: bool


@dataclass(frozen=True)
class RunStart:
    epoch: int
    resuming: bool
    phase: int
    started: bool


def is_half(run: EpochRunRow | None, epoch: int) -> bool:
    return run is not None and run.epoch == epoch and not run.finished and (run.phase > EpochPhase.NOT_STARTED or run.started)


async def half_epoch(session: AsyncSession) -> HalfEpoch | None:
    cosmos = await CosmosRepository(session).get()
    if cosmos is None:
        return None
    run = await run_of(session, cosmos.epoch)
    if run is None or not is_half(run, cosmos.epoch):
        return None
    return HalfEpoch(run.epoch, run.phase, run.started)


async def begin_run(session: AsyncSession) -> RunStart:
    cosmos = await CosmosRepository(session).require_cosmos()
    with acting(ActorKind.SYSTEM, None, cosmos.epoch, key="epoch.begin"):
        run = await run_of(session, cosmos.epoch)
        resuming = is_half(run, cosmos.epoch)
        if run is not None and run.finished:
            run.finished = False
            run.phase = EpochPhase.NOT_STARTED
            run.started = False
        run = await require_run(session, cosmos.epoch)
        await plan_steps(session, cosmos.epoch)
        run.resumed = run.resumed or resuming
        if run.started_at is None:
            run.started_at = datetime.now(UTC)
        await session.flush()
    return RunStart(cosmos.epoch, resuming, run.phase, run.started)


async def requeue_intuitions(session: AsyncSession) -> int:
    rows = list(await session.scalars(select(HorizonIntuitionRow.id).where(HorizonIntuitionRow.status == HorizonStatus.PROCESSING)))
    if rows:
        await session.execute(update(HorizonIntuitionRow).where(HorizonIntuitionRow.id.in_(rows)).values(status=HorizonStatus.PENDING))
    return len(rows)


async def stale_runs(session: AsyncSession) -> list[EpochRunRow]:
    cosmos = await CosmosRepository(session).require_cosmos()
    return list(await session.scalars(select(EpochRunRow).where(EpochRunRow.epoch < cosmos.epoch, EpochRunRow.finished.is_(False))))
