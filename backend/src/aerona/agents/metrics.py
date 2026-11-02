from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from aerona.agents.roles import role_of
from aerona.db.telemetry.setup import TelemetryDatabase
from aerona.db.telemetry.tables import LlmCallRow
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
        cost_usd=record.usage.cost_usd,
        actions=actions,
        error=(record.error or "")[:METRIC_ERROR_CHARS] or None,
    )


class TelemetrySink:
    def __init__(self, telemetry: TelemetryDatabase) -> None:
        self._telemetry = telemetry

    async def __call__(self, record: CallRecord) -> None:
        async with self._telemetry.sessions() as session, session.begin():
            session.add(call_row(record, current_epoch.get(), current_actions.get()))
