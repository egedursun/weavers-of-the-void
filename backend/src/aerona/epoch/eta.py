from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.epochs import EpochPhaseTimingRow, EpochRunRow
from aerona.domain.enums.epoch import EpochPhase
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class EpochEstimate:
    samples: int
    average_epoch_seconds: float | None
    average_phase_start_seconds: dict[int, float] = field(default_factory=dict)
    running: bool = False
    elapsed_seconds: float | None = None
    remaining_seconds: int | None = None
    phase: int | None = None
    overrun: bool = False


async def phase_started(session: AsyncSession, epoch: int, phase: EpochPhase, offset: float) -> None:
    row = await session.get(EpochPhaseTimingRow, (epoch, int(phase)))
    if row is None:
        session.add(EpochPhaseTimingRow(epoch=epoch, phase=int(phase), started_offset_seconds=offset))
    else:
        row.started_offset_seconds = offset
        row.duration_seconds = None


async def phase_finished(session: AsyncSession, epoch: int, phase: EpochPhase, offset: float) -> None:
    row = await session.get(EpochPhaseTimingRow, (epoch, int(phase)))
    if row is not None:
        row.duration_seconds = max(0.0, offset - row.started_offset_seconds)


def run_seconds(run: EpochRunRow) -> float | None:
    if run.started_at is None or run.finished_at is None:
        return None
    start = run.started_at if run.started_at.tzinfo else run.started_at.replace(tzinfo=UTC)
    end = run.finished_at if run.finished_at.tzinfo else run.finished_at.replace(tzinfo=UTC)
    return (end - start).total_seconds()


async def estimate(session: AsyncSession, rules: Rules, current_epoch: int | None = None, now: datetime | None = None) -> EpochEstimate:
    runs = list(
        await session.scalars(
            select(EpochRunRow)
            .where(EpochRunRow.finished.is_(True), EpochRunRow.resumed.is_(False))
            .order_by(EpochRunRow.epoch.desc())
            .limit(rules.metrics.eta_average_epochs)
        )
    )
    totals = [seconds for seconds in (run_seconds(run) for run in runs) if seconds is not None]
    starts: dict[int, list[float]] = defaultdict(list)
    if runs:
        rows = await session.scalars(select(EpochPhaseTimingRow).where(EpochPhaseTimingRow.epoch.in_([run.epoch for run in runs])))
        for row in rows:
            starts[row.phase].append(row.started_offset_seconds)
    average_total = sum(totals) / len(totals) if totals else None
    average_starts = {phase: sum(values) / len(values) for phase, values in starts.items()}
    running = await session.get(EpochRunRow, current_epoch) if current_epoch is not None else None
    if running is None or running.finished or running.started_at is None or average_total is None:
        return EpochEstimate(len(totals), average_total, average_starts)
    moment = now or datetime.now(UTC)
    began = running.started_at if running.started_at.tzinfo else running.started_at.replace(tzinfo=UTC)
    elapsed = (moment - began).total_seconds()
    current = await session.scalar(
        select(EpochPhaseTimingRow).where(EpochPhaseTimingRow.epoch == running.epoch).order_by(EpochPhaseTimingRow.phase.desc()).limit(1)
    )
    if current is not None and current.phase in average_starts:
        remaining = average_total - average_starts[current.phase] - max(0.0, elapsed - current.started_offset_seconds)
    else:
        remaining = average_total - elapsed
    return EpochEstimate(
        samples=len(totals),
        average_epoch_seconds=average_total,
        average_phase_start_seconds=average_starts,
        running=True,
        elapsed_seconds=elapsed,
        remaining_seconds=max(0, round(remaining)),
        phase=current.phase if current is not None else None,
        overrun=remaining < 0,
    )
