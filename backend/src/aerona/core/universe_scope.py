from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

CURRENT_UNIVERSE: ContextVar[str | None] = ContextVar("aerona_current_universe", default=None)


def current_universe() -> str | None:
    return CURRENT_UNIVERSE.get()


@contextmanager
def in_universe(universe_id: str | None) -> Iterator[None]:
    token = CURRENT_UNIVERSE.set(universe_id)
    try:
        yield
    finally:
        CURRENT_UNIVERSE.reset(token)


def enter_universe(universe_id: str | None) -> None:
    CURRENT_UNIVERSE.set(universe_id)
