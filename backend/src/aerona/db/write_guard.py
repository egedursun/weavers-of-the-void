from collections.abc import Callable, Iterable
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import ColumnElement, true
from sqlalchemy.orm import InstrumentedAttribute

WRITE_GUARD: ContextVar[Callable[[int, str], bool] | None] = ContextVar("write_guard", default=None)


@dataclass(frozen=True)
class HeldScope:
    only: int | None
    nodes: frozenset[int]


HELD_SCOPE: ContextVar[HeldScope | None] = ContextVar("held_scope", default=None)
NodeColumn = ColumnElement[int] | InstrumentedAttribute[int] | InstrumentedAttribute[int | None]


def write_blocked(node_id: int, key: str) -> bool:
    guard = WRITE_GUARD.get()
    return guard is not None and guard(node_id, key)


def held(*node_ids: int | None) -> bool:
    scope = HELD_SCOPE.get()
    if scope is None:
        return False
    return any(node_id is not None and (node_id != scope.only if scope.only is not None else node_id in scope.nodes) for node_id in node_ids)


def free_rows(column: NodeColumn) -> ColumnElement[bool]:
    scope = HELD_SCOPE.get()
    if scope is None:
        return true()
    if scope.only is not None:
        return column == scope.only
    return column.notin_(sorted(scope.nodes)) if scope.nodes else true()


class Identified(Protocol):
    id: int


def unheld[T: Identified](rows: Iterable[T]) -> list[T]:
    return [row for row in rows if not held(row.id)]
