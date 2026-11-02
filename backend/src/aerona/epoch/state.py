from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.epochs import EpochEnginePhaseRow, EpochRunRow, EpochStepRow
from aerona.domain.enums.epoch import EngineStage, EpochPhase, EpochStepKind, EpochStepStatus

DONE_STATUSES = frozenset({EpochStepStatus.DONE, EpochStepStatus.SKIPPED})


async def run_of(session: AsyncSession, epoch: int) -> EpochRunRow | None:
    return await session.get(EpochRunRow, epoch)


async def require_run(session: AsyncSession, epoch: int) -> EpochRunRow:
    run = await run_of(session, epoch)
    if run is None:
        run = EpochRunRow(epoch=epoch, phase=EpochPhase.NOT_STARTED, started=False, finished=False, engine_notes=[])
        session.add(run)
        await session.flush()
    return run


async def step_status(session: AsyncSession, epoch: int, step: EpochStepKind) -> EpochStepStatus | None:
    row = await session.get(EpochStepRow, (epoch, step))
    return row.status if row is not None else None


async def step_settled(session: AsyncSession, epoch: int, step: EpochStepKind) -> bool:
    return await step_status(session, epoch, step) in DONE_STATUSES


async def attempted(session: AsyncSession, epoch: int, step: EpochStepKind) -> bool:
    return await step_status(session, epoch, step) is not None


async def mark_step(session: AsyncSession, epoch: int, step: EpochStepKind, status: EpochStepStatus, error: str | None = None) -> None:
    await require_run(session, epoch)
    row = await session.get(EpochStepRow, (epoch, step))
    if row is None:
        session.add(EpochStepRow(epoch=epoch, step=step, status=status, error=error))
    else:
        row.status = status
        row.error = error
    await session.flush()


async def raise_phase(session: AsyncSession, epoch: int, phase: EpochPhase) -> None:
    run = await require_run(session, epoch)
    run.phase = max(run.phase, int(phase))


async def finish_run(session: AsyncSession, epoch: int) -> None:
    run = await require_run(session, epoch)
    run.phase = max(run.phase, int(EpochPhase.TRANSITION))
    run.finished = True
    run.finished_at = datetime.now(UTC)


async def engine_phases_done(session: AsyncSession, epoch: int, stage: EngineStage) -> set[str]:
    rows = await session.scalars(select(EpochEnginePhaseRow.phase).where(EpochEnginePhaseRow.epoch == epoch, EpochEnginePhaseRow.stage == stage))
    return set(rows)


async def mark_engine_phase(session: AsyncSession, epoch: int, stage: EngineStage, phase: str, seconds: float) -> None:
    await require_run(session, epoch)
    session.add(EpochEnginePhaseRow(epoch=epoch, stage=stage, phase=phase, seconds=seconds))
