from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class ActNote:
    reason: str | None = None
    expected_revision: int | None = None


CURRENT_NOTE: ContextVar[ActNote | None] = ContextVar("act_note", default=None)
BLANK = ActNote()


def current_note() -> ActNote:
    return CURRENT_NOTE.get() or BLANK


@contextmanager
def noting(note: ActNote) -> Iterator[ActNote]:
    token = CURRENT_NOTE.set(note)
    try:
        yield note
    finally:
        CURRENT_NOTE.reset(token)
