from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session
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


def install_flush_batching() -> None:
    for hook in (hold_profile_columns, align_updates):
        if not event.contains(Session, "before_flush", hook):
            event.listen(Session, "before_flush", hook)


install_flush_batching()
