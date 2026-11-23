from dataclasses import dataclass
from functools import cache
from typing import Any

from sqlalchemy import Table, delete, event
from sqlalchemy.orm import Mapper, Session, object_mapper
from sqlalchemy.orm.attributes import instance_state, set_committed_value

from aerona.db.base import Base

CASCADE = "CASCADE"
SET_NULL = "SET NULL"


@dataclass(frozen=True)
class Follower:
    child: type[Any]
    child_key: str
    parent_key: str
    removes: bool


def parent_key(mapper: Mapper[Any], column: Any) -> str | None:
    found = mapper.get_property_by_column(column) if column in mapper.columns.values() else None
    return found.key if found is not None else None


@cache
def followers() -> dict[type[Any], tuple[Follower, ...]]:
    by_table: dict[Table, list[tuple[type[Any], str, Any, bool]]] = {}
    for mapper in Base.registry.mappers:
        for column in mapper.columns:
            child_key = mapper.get_property_by_column(column).key
            for foreign in column.foreign_keys:
                mode = (foreign.ondelete or "").upper()
                if mode in (CASCADE, SET_NULL) and isinstance(foreign.column.table, Table):
                    by_table.setdefault(foreign.column.table, []).append((mapper.class_, child_key, foreign.column, mode == CASCADE))
    found: dict[type[Any], tuple[Follower, ...]] = {}
    for mapper in Base.registry.mappers:
        rows = [
            Follower(child, child_key, key, removes)
            for table in mapper.tables
            if isinstance(table, Table)
            for child, child_key, column, removes in by_table.get(table, [])
            if (key := parent_key(mapper, column)) is not None
        ]
        if rows:
            found[mapper.class_] = tuple(rows)
    return found


def follow_cascades(session: Session, _context: object) -> None:
    table = followers()
    frontier = [row for row in session.deleted if type(row) in table]
    gone: set[int] = {id(row) for row in session.deleted}
    while frontier:
        wanted: dict[tuple[type[Any], str], tuple[set[Any], bool]] = {}
        for row in frontier:
            for follower in table.get(type(row), ()):
                value = instance_state(row).dict.get(follower.parent_key)
                if value is not None:
                    wanted.setdefault((follower.child, follower.child_key), (set(), follower.removes))[0].add(value)
        frontier = []
        if not wanted:
            break
        classes = {child for child, _key in wanted}
        for row in list(session.identity_map.values()):
            if row is None or type(row) not in classes or id(row) in gone:
                continue
            for (child, key), (values, removes) in wanted.items():
                if type(row) is not child or instance_state(row).dict.get(key) not in values:
                    continue
                if removes:
                    gone.add(id(row))
                    session.expunge(row)
                    frontier.append(row)
                    break
                set_committed_value(row, key, None)


def deleted_parents(deleted: list[Any]) -> dict[int, set[int]]:
    table = followers()
    owners: dict[tuple[type[Any], str, Any], list[int]] = {}
    for row in deleted:
        for follower in table.get(type(row), ()):
            value = instance_state(row).dict.get(follower.parent_key)
            if follower.removes and value is not None:
                owners.setdefault((follower.child, follower.child_key, value), []).append(id(row))
    if not owners:
        return {}
    keys_by_child: dict[type[Any], set[str]] = {}
    for child, key, _value in owners:
        keys_by_child.setdefault(child, set()).add(key)
    found: dict[int, set[int]] = {}
    for row in deleted:
        for key in sorted(keys_by_child.get(type(row), ())):
            parents = owners.get((type(row), key, instance_state(row).dict.get(key)), [])
            mine = {parent for parent in parents if parent != id(row)}
            if mine:
                found.setdefault(id(row), set()).update(mine)
    return found


def delete_children_first(session: Session, _context: object, _instances: object) -> None:
    deleted = list(session.deleted)
    if len(deleted) < 2:
        return
    parents = deleted_parents(deleted)
    pending = [row for row in deleted if id(row) in parents]
    while pending:
        above = {parent for row in pending for parent in parents[id(row)]}
        lowest = [row for row in pending if id(row) not in above] or pending
        for row in lowest:
            mapper = object_mapper(row)
            identity = instance_state(row).identity
            if identity is not None:
                matches = [column == value for column, value in zip(mapper.primary_key, identity, strict=True)]
                session.execute(delete(type(row)).where(*matches), execution_options={"synchronize_session": False})
            session.expunge(row)
        done = {id(row) for row in lowest}
        pending = [row for row in pending if id(row) not in done]


def install_cascade_following() -> None:
    if not event.contains(Session, "after_flush", follow_cascades):
        event.listen(Session, "after_flush", follow_cascades)
    if not event.contains(Session, "before_flush", delete_children_first):
        event.listen(Session, "before_flush", delete_children_first)
