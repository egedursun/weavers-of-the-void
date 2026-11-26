from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.roles import role_of
from aerona.db.telemetry.setup import LIFETIME_ID, TelemetryDatabase
from aerona.db.telemetry.tables import LlmCallRow, UsageTotalsRow
from aerona.domain.enums.telemetry import LlmCallKind, LlmCallStatus
from aerona.llm.records import CallKind, CallOutcome, CallRecord

MILLISECONDS = 1000
METRIC_ERROR_CHARS = 200

current_epoch: ContextVar[int | None] = ContextVar("current_epoch", default=None)
current_actions: ContextVar[int | None] = ContextVar("current_actions", default=None)


@contextmanager
def metrics_epoch(epoch: int | None) -> Iterator[None]:
    token = current_epoch.set(epoch)
    try:
        yield
    finally:
        current_epoch.reset(token)


@contextmanager
def metrics_turn(epoch: int, actions: int) -> Iterator[None]:
    epoch_token = current_epoch.set(epoch)
    actions_token = current_actions.set(actions)
    try:
        yield
    finally:
        current_actions.reset(actions_token)
        current_epoch.reset(epoch_token)


def call_status(record: CallRecord) -> LlmCallStatus:
    if record.outcome is not CallOutcome.OK:
        return LlmCallStatus.ERROR
    return LlmCallStatus.OK if record.usage.completed else LlmCallStatus.PARTIAL


def call_row(record: CallRecord, epoch: int | None, actions: int | None) -> LlmCallRow:
    return LlmCallRow(
        epoch=epoch,
        job=record.label,
        role=role_of(record.label),
        model=record.model,
        kind=LlmCallKind.AGENT if record.kind is CallKind.AGENT else LlmCallKind.STRUCTURED,
        status=call_status(record),
        duration_ms=max(0, round(record.duration_seconds * MILLISECONDS)),
        attempts=max(1, record.attempts),
        turns=record.usage.turns or None,
        input_tokens=record.usage.input_tokens,
        output_tokens=record.usage.output_tokens,
        actions=actions,
        error=(record.error or "")[:METRIC_ERROR_CHARS] or None,
    )


async def count_lifetime(session: AsyncSession, tokens: int) -> None:
    if await session.get(UsageTotalsRow, LIFETIME_ID) is None:
        session.add(UsageTotalsRow(id=LIFETIME_ID, tokens=tokens, calls=1))
        return
    await session.execute(
        update(UsageTotalsRow)
        .where(UsageTotalsRow.id == LIFETIME_ID)
        .values(tokens=UsageTotalsRow.tokens + tokens, calls=UsageTotalsRow.calls + 1)
        .execution_options(synchronize_session=False)
    )


class TelemetrySink:
    def __init__(self, telemetry: TelemetryDatabase) -> None:
        self._telemetry = telemetry

    async def __call__(self, record: CallRecord) -> None:
        async with self._telemetry.sessions() as session, session.begin():
            row = call_row(record, current_epoch.get(), current_actions.get())
            session.add(row)
            await count_lifetime(session, row.input_tokens + row.output_tokens)
