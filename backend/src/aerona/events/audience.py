from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from aerona.events.kinds import EventKind

PRIVATE_KINDS = frozenset(
    {
        EventKind.AGENT_RETRY,
        EventKind.AGENT_STREAM,
        EventKind.AGENT_THOUGHT,
        EventKind.AGENT_TOOL_PREPARING,
        EventKind.AGENT_TOOL_WRITING,
        EventKind.AGENT_TOOL_CALLED,
        EventKind.AGENT_TOOL_RESULT,
        EventKind.AGENT_WRITING,
        EventKind.DIVINE_WILL_CYCLE_STARTED,
        EventKind.DIVINE_WILL_CYCLE_FINISHED,
        EventKind.DIVINE_WILL_CONFIRMATION_REQUESTED,
        EventKind.DIVINE_WILL_ARTIFACT_CHANGED,
        EventKind.DIVINE_WILL_PLAN_CHANGED,
        EventKind.DIVINE_WILL_FORECAST_PROGRESS,
        EventKind.PRESENCE_SESSION_CHANGED,
        EventKind.PRESENCE_EXCHANGE_STARTED,
        EventKind.PRESENCE_EXCHANGE_FINISHED,
    }
)
EVENT_AUDIENCE: ContextVar[int | None] = ContextVar("event_audience", default=None)


@contextmanager
def addressed_to(account_id: int | None) -> Iterator[None]:
    token = EVENT_AUDIENCE.set(account_id)
    try:
        yield
    finally:
        EVENT_AUDIENCE.reset(token)


def audience_for(kind: EventKind, explicit: int | None) -> int | None:
    if kind not in PRIVATE_KINDS:
        return None
    return explicit if explicit is not None else EVENT_AUDIENCE.get()


def private_audience(author_account_id: int | None, shared: bool) -> int | None:
    return None if shared else author_account_id


def reaches(audience: int | None, account_id: int | None) -> bool:
    return audience is None or account_id is None or audience == account_id
