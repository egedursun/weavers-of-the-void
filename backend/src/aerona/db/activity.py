from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, UOWTransaction

from aerona.core.activity import ActivityLog, current_activity
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.meta import ImageRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonPowerRow
from aerona.domain.enums.bond import BondState

PAINTED = "painted"
CREATED = "created"
POWERS = "powers written"
LINKED = "linked"
UNLINKED = "unlinked"
RETYPED = "bond retyped"
TRACKED = {
    "depth": "deepened",
    "image_prompt": "image prompt written",
    "epic": "epic written",
    "appearance": "likeness written",
    "name": "named",
    "status": "status changed",
}


def _value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _changed(row: Any, attribute: str) -> tuple[Any, Any] | None:
    state = inspect(row)
    if attribute not in state.attrs:
        return None
    history = state.attrs[attribute].history
    if not history.has_changes():
        return None
    before = history.deleted[0] if history.deleted else None
    after = history.added[0] if history.added else None
    return before, after


def _record_new(log: ActivityLog, row: Any) -> None:
    if isinstance(row, ImageRow):
        log.record(row.target_node_id, PAINTED)
    elif isinstance(row, EntityRow):
        log.record(row.id, CREATED)
    elif isinstance(row, SonPowerRow):
        log.record(row.son_id, POWERS)
    elif isinstance(row, BondRow):
        log.record(row.source_node_id, LINKED, other_id=row.target_node_id, note=_value(row.kind))


def _record_dirty(log: ActivityLog, row: Any) -> None:
    if isinstance(row, NodeRow):
        for attribute, action in TRACKED.items():
            change = _changed(row, attribute)
            if change is None:
                continue
            before, after = change
            if attribute == "name" and before:
                log.record(row.id, action, note=f"{before} → {after}")
            elif attribute == "status":
                log.record(row.id, action, note=_value(after))
            else:
                log.record(row.id, action)
    elif isinstance(row, BondRow):
        state = _changed(row, "state")
        if state is not None and state[1] is not BondState.ACTIVE:
            log.record(row.source_node_id, UNLINKED, other_id=row.target_node_id, note=_value(row.kind))
        kind = _changed(row, "kind")
        if kind is not None:
            log.record(row.source_node_id, RETYPED, other_id=row.target_node_id, note=_value(kind[1]))


def capture_activity(session: Session, flush_context: UOWTransaction) -> None:
    log = current_activity()
    if log is None:
        return
    for row in session.new:
        _record_new(log, row)
    for row in session.dirty:
        _record_dirty(log, row)


def install_activity_capture() -> None:
    if not event.contains(Session, "after_flush", capture_activity):
        event.listen(Session, "after_flush", capture_activity)
