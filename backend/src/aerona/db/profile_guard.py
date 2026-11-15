from dataclasses import dataclass
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Mapper, Session, UOWTransaction, object_mapper
from sqlalchemy.orm.attributes import get_history, set_committed_value
from sqlalchemy.orm.base import instance_state

from aerona.db.base import Base
from aerona.db.write_guard import RESTORED, WRITE_GUARD, guard_idle, write_blocked

ENTITY_TABLE = "entities"
NODE_TABLES = frozenset({"nodes", ENTITY_TABLE, "sons", "worlds", "stars", "foreign_gods", "creator"})
LOCK_COLUMN = "locked"
KEY_SEPARATOR = "."
EXPLICIT_NODE_COLUMNS: dict[str, str] = {}
UNGUARDED_TABLES: set[str] = set()


@dataclass(frozen=True)
class ProfileShape:
    table: str
    node_column: str
    columns: tuple[str, ...]
    lockable: bool


SHAPES: dict[str, ProfileShape | None] = {}


@dataclass(frozen=True)
class OwnedShape:
    table: str
    owners: tuple[str, ...]
    columns: tuple[str, ...]


OWNED: dict[str, OwnedShape | None] = {}


def profile_key(table: str, column: str) -> str:
    return f"{table}{KEY_SEPARATOR}{column}"


def register_profile_table(table: str, node_column: str) -> None:
    EXPLICIT_NODE_COLUMNS[table] = node_column
    SHAPES.pop(table, None)


def table_name(mapper: Mapper[Any]) -> str:
    return str(getattr(mapper.class_, "__tablename__", ""))


def _auto_node_column(mapper: Mapper[Any]) -> str | None:
    keys = list(mapper.primary_key)
    if len(keys) != 1:
        return None
    column = keys[0]
    if any(foreign.column.table.name == ENTITY_TABLE for foreign in column.foreign_keys):
        return mapper.get_property_by_column(column).key
    return None


def _shape(mapper: Mapper[Any]) -> ProfileShape | None:
    table = table_name(mapper)
    if table in SHAPES:
        return SHAPES[table]
    shape: ProfileShape | None = None
    if table not in UNGUARDED_TABLES:
        node_column = EXPLICIT_NODE_COLUMNS.get(table) or _auto_node_column(mapper)
        if node_column is not None:
            columns = tuple(attribute.key for attribute in mapper.column_attrs if attribute.key not in {node_column, LOCK_COLUMN})
            shape = ProfileShape(table, node_column, columns, LOCK_COLUMN in mapper.column_attrs)
    SHAPES[table] = shape
    return shape


def shape_of_table(table: str) -> ProfileShape | None:
    for mapper in Base.registry.mappers:
        if table_name(mapper) == table:
            return _shape(mapper)
    return None


def profile_mapper(table: str) -> Mapper[Any] | None:
    return next((mapper for mapper in Base.registry.mappers if table_name(mapper) == table), None)


def owned_shape(mapper: Mapper[Any]) -> OwnedShape | None:
    table = table_name(mapper)
    if table in OWNED:
        return OWNED[table]
    owners = tuple(
        mapper.get_property_by_column(column).key
        for column in mapper.local_table.columns
        if any(foreign.column.table.name in NODE_TABLES for foreign in column.foreign_keys)
    )
    keys = {mapper.get_property_by_column(column).key for column in mapper.primary_key}
    columns = tuple(attribute.key for attribute in mapper.column_attrs if attribute.key not in keys and attribute.key != LOCK_COLUMN)
    shape = OwnedShape(table, owners, columns) if owners and table not in UNGUARDED_TABLES else None
    OWNED[table] = shape
    return shape


def owner_ids(row: object, shape: OwnedShape) -> list[int]:
    found: list[int] = []
    for key in shape.owners:
        history = get_history(row, key)
        value = history.deleted[0] if history.deleted else getattr(row, key)
        if isinstance(value, int):
            found.append(value)
    return found


def held_columns(row: object) -> frozenset[str]:
    value = getattr(row, LOCK_COLUMN, None)
    return frozenset(item for item in value if isinstance(item, str)) if isinstance(value, list | tuple | set | frozenset) else frozenset()


def standing_locks(row: object) -> frozenset[str]:
    state = instance_state(row)
    if LOCK_COLUMN not in state.mapper.column_attrs:
        return frozenset()
    if LOCK_COLUMN not in state.committed_state:
        return held_columns(row)
    history = get_history(row, LOCK_COLUMN)
    if not history.has_changes():
        return held_columns(row)
    before = history.deleted[0] if history.deleted else None
    return frozenset(item for item in before if isinstance(item, str)) if isinstance(before, list | tuple | set | frozenset) else frozenset()


def profile_held(row: object, column: str) -> bool:
    shape = _shape(object_mapper(row))
    if shape is None:
        return False
    if column in held_columns(row):
        return True
    return write_blocked(int(getattr(row, shape.node_column)), profile_key(shape.table, column))


def column_frozen(row: object, column: str) -> bool:
    if column in held_columns(row):
        return True
    mapper = object_mapper(row)
    shape = _shape(mapper)
    if shape is not None:
        node_id = getattr(row, shape.node_column)
        return node_id is not None and write_blocked(int(node_id), profile_key(shape.table, column))
    owned = owned_shape(mapper)
    return owned is not None and any(write_blocked(node_id, profile_key(owned.table, column)) for node_id in owner_ids(row, owned))


def restore_owned(row: object) -> list[str]:
    state = instance_state(row)
    shape = owned_shape(state.mapper)
    if shape is None or state.pending or (guard_idle() and not standing_locks(row)):
        return []
    changed = [column for column in shape.columns if column in state.committed_state]
    if not changed:
        return []
    owners: list[int] | None = None
    held = standing_locks(row)
    restored: list[str] = []
    for column in changed:
        if column not in held:
            owners = owner_ids(row, shape) if owners is None else owners
            if not any(write_blocked(node_id, profile_key(shape.table, column)) for node_id in owners):
                continue
        history = get_history(row, column)
        if history.deleted and history.has_changes():
            set_committed_value(row, column, history.deleted[0])
            restored.append(column)
    return restored


def restore_held(row: object) -> list[str]:
    state = instance_state(row)
    shape = _shape(state.mapper)
    if shape is None or state.pending:
        return restore_owned(row)
    if guard_idle() and not standing_locks(row):
        return []
    changed = [column for column in shape.columns if column in state.committed_state]
    if not changed:
        return []
    node_id = getattr(row, shape.node_column)
    if node_id is None:
        return []
    held = standing_locks(row)
    restored: list[str] = []
    for column in changed:
        if column not in held and not write_blocked(int(node_id), profile_key(shape.table, column)):
            continue
        history = get_history(row, column)
        if history.deleted and history.has_changes():
            set_committed_value(row, column, history.deleted[0])
            restored.append(column)
    return restored


@event.listens_for(Session, "before_flush")
def hold_profile_columns(session: Session, flush_context: UOWTransaction, instances: object) -> None:
    if WRITE_GUARD.get() is None:
        return
    restored = RESTORED.get()
    for state in list(session.identity_map._modified):
        if state not in session._deleted:
            columns = restore_held(state.obj())
            if restored is not None:
                restored.extend(profile_key(table_name(state.mapper), column) for column in columns)
