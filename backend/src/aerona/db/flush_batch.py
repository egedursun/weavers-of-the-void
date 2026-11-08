from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.base import instance_state

from aerona.db.profile_guard import hold_profile_columns
from aerona.db.read_memo import KEEP_KEY


def changed_columns(state: Any) -> frozenset[str]:
    columns = state.mapper.column_attrs
    return frozenset(
        key for key in state.committed_state if key in columns and state.attrs[key].history.has_changes() and not columns[key].columns[0].primary_key
    )


def align_updates(sync: Session, *_: object) -> None:
    if KEEP_KEY not in sync.info:
        return
    groups: dict[Any, list[tuple[Any, frozenset[str]]]] = {}
    for row in sync.dirty:
        state = instance_state(row)
        changed = changed_columns(state)
        if changed:
            groups.setdefault(state.mapper, []).append((state, changed))
    for rows in groups.values():
        if len(rows) < 2:
            continue
        union = frozenset().union(*(changed for _, changed in rows))
        for state, changed in rows:
            for key in union - changed:
                if key in state.dict:
                    flag_modified(state.obj(), key)


def install_flush_batching() -> None:
    for hook in (hold_profile_columns, align_updates):
        if not event.contains(Session, "before_flush", hook):
            event.listen(Session, "before_flush", hook)


install_flush_batching()
