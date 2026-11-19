from typing import Any

from sqlalchemy import Column, Integer, event, func, inspect, select
from sqlalchemy.orm import Mapper, Session
from sqlalchemy.orm.attributes import flag_modified

from aerona.db.attr_history import changed
from aerona.db.profile_guard import hold_profile_columns
from aerona.db.read_memo import KEEP_KEY, DirtyStates


def changed_columns(state: Any) -> frozenset[str]:
    columns = state.mapper.column_attrs
    return frozenset(key for key in state.committed_state if key in columns and changed(state, key) and not columns[key].columns[0].primary_key)


def align_updates(sync: Session, *_: object) -> None:
    if KEEP_KEY not in sync.info:
        return
    modified = sync.identity_map._modified
    shared = {mapper for mapper, count in modified.mappers.items() if count > 1} if isinstance(modified, DirtyStates) else None
    if shared is not None and not shared:
        return
    groups: dict[Any, list[tuple[Any, frozenset[str]]]] = {}
    for state in list(modified):
        if state in sync._deleted or (shared is not None and state.mapper not in shared):
            continue
        edited = changed_columns(state)
        if edited:
            groups.setdefault(state.mapper, []).append((state, edited))
    for rows in groups.values():
        if len(rows) < 2:
            continue
        union = frozenset().union(*(edited for _, edited in rows))
        for state, edited in rows:
            for key in union - edited:
                if key in state.dict:
                    flag_modified(state.obj(), key)


NUMBERED_AT_ONCE = 3


def own_key(mapper: Mapper[Any]) -> Column[Any] | None:
    keys = mapper.primary_key
    if mapper.inherits is not None or len(mapper.self_and_descendants) > 1 or len(keys) != 1:
        return None
    key = keys[0]
    if key.foreign_keys or not isinstance(key.type, Integer) or key.autoincrement not in (True, "auto") or not isinstance(key, Column):
        return None
    return key


def number_inserts(sync: Session, *_: object) -> None:
    groups: dict[Mapper[Any], list[Any]] = {}
    for instance in sync.new:
        state = inspect(instance)
        groups.setdefault(state.mapper, []).append(state)
    for mapper, states in groups.items():
        key = own_key(mapper) if len(states) >= NUMBERED_AT_ONCE else None
        if key is None:
            continue
        name = mapper.get_property_by_column(key).key
        fresh = sorted((state for state in states if state.dict.get(name) is None), key=lambda state: state.insert_order)
        if len(fresh) < NUMBERED_AT_ONCE:
            continue
        top = int(sync.connection().execute(select(func.coalesce(func.max(key), 0))).scalar_one())
        for offset, state in enumerate(fresh, start=1):
            setattr(state.obj(), name, top + offset)


def install_flush_batching() -> None:
    for hook in (hold_profile_columns, align_updates, number_inserts):
        if not event.contains(Session, "before_flush", hook):
            event.listen(Session, "before_flush", hook)


install_flush_batching()
