from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, cast

from sqlalchemy import Select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import functions
from sqlalchemy.sql.compiler import SQLCompiler

INSTALLED: set[str] = set()
AGGREGATES = frozenset({"count", "sum", "min", "max", "avg", "total", "group_concat"})


def aggregate(column: Any) -> bool:
    inner = getattr(column, "element", column)
    return isinstance(inner, functions.FunctionElement) and str(inner.name).lower() in AGGREGATES


def read_order(statement: Select[Any]) -> list[Any]:
    if statement._group_by_clauses:
        return list(statement._group_by_clauses)
    columns = list(statement.selected_columns)
    if columns and all(aggregate(column) for column in columns):
        return []
    keys: list[Any] = []
    for source in statement.get_final_froms():
        primary = list(getattr(source, "primary_key", ()))
        if not primary:
            return [column for column in columns if not aggregate(column)]
        keys.extend(primary)
    return keys


ORDERING: ContextVar[bool] = ContextVar("aerona_ordering_read", default=False)


def ordered_select(statement: Select[Any], compiler: SQLCompiler, **kw: Any) -> str:
    if not compiler.stack and not statement._order_by_clauses and not ORDERING.get():
        token = ORDERING.set(True)
        try:
            keys = read_order(statement)
        finally:
            ORDERING.reset(token)
        if keys:
            statement = statement.order_by(*keys)
    visit = cast(Callable[..., str], compiler.visit_select)
    return visit(statement, **kw)


def install_ordered_reads() -> None:
    if "select" not in INSTALLED:
        compiles(Select)(ordered_select)
        INSTALLED.add("select")
