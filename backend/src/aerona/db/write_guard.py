from collections.abc import Callable
from contextvars import ContextVar

WRITE_GUARD: ContextVar[Callable[[int, str], bool] | None] = ContextVar("write_guard", default=None)


def write_blocked(node_id: int, key: str) -> bool:
    guard = WRITE_GUARD.get()
    return guard is not None and guard(node_id, key)
