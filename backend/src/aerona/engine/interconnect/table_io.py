from typing import Any

from sqlalchemy import Join, Table, event
from sqlalchemy.orm import ORMExecuteState, Session

from aerona.engine.interconnect.guards import READ_MODE, WRITE_MODE, observed

TABLE_PREFIX = "table"
_INSTALLED: list[bool] = []


def table_names(item: Any) -> set[str]:
    if isinstance(item, Table):
        return {item.name}
    if isinstance(item, Join):
        return table_names(item.left) | table_names(item.right)
    froms = getattr(item, "get_final_froms", None)
    if froms is not None:
        return {name for inner in froms() for name in table_names(inner)}
    element = getattr(item, "element", None)
    return table_names(element) if element is not None and element is not item else set()


def _tables_of(state: ORMExecuteState) -> set[str]:
    statement: Any = state.statement
    return {name for item in getattr(statement, "get_final_froms", lambda: [])() for name in table_names(item)}


def _on_execute(state: ORMExecuteState) -> None:
    mode = READ_MODE if state.is_select else WRITE_MODE
    for name in _tables_of(state):
        observed(TABLE_PREFIX, name, mode)


def _on_flush(session: Session, *_: object) -> None:
    for item in (*session.new, *session.dirty, *session.deleted):
        table = getattr(type(item), "__tablename__", None)
        if isinstance(table, str):
            observed(TABLE_PREFIX, table, WRITE_MODE)


def install_table_recorder() -> None:
    if _INSTALLED:
        return
    event.listen(Session, "do_orm_execute", _on_execute)
    event.listen(Session, "before_flush", _on_flush)
    _INSTALLED.append(True)
