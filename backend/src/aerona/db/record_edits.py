import threading
from typing import Any

from sqlalchemy import Delete, Table, Update, event, select
from sqlalchemy.orm import ORMExecuteState, Session, UOWTransaction
from sqlalchemy.orm.base import instance_state

INCIDENT = "incident"
STEP = "step"
LINE = "line"
RECORD_KEYS: dict[str, tuple[str, str]] = {
    "incidents": ("id", INCIDENT),
    "incident_participants": ("incident_id", INCIDENT),
    "incident_facts": ("incident_id", INCIDENT),
    "incident_steps": ("incident_id", INCIDENT),
    "incident_terms": ("incident_id", INCIDENT),
    "incident_step_states": ("step_id", STEP),
    "chronicle": ("id", LINE),
    "chronicle_entities": ("chronicle_id", LINE),
}

Edit = tuple[str, int]
PENDING = "aerona.record_edits"

_LOCK = threading.Lock()
_WATCHED: dict[str, set[Edit]] = {}


def url_of(session: Session) -> str:
    return session.get_bind().engine.url.render_as_string(hide_password=False)


def watch(url: str) -> None:
    with _LOCK:
        _WATCHED.setdefault(url, set())


def unwatch(url: str) -> None:
    with _LOCK:
        _WATCHED.pop(url, None)


def drain(url: str) -> set[Edit]:
    with _LOCK:
        found = _WATCHED.get(url)
        if found is None:
            return set()
        _WATCHED[url] = set()
        return found


def hold(session: Session, url: str, edits: set[Edit]) -> None:
    if edits:
        session.info.setdefault(PENDING, {}).setdefault(url, set()).update(edits)


@event.listens_for(Session, "after_commit")
def release_edits(session: Session) -> None:
    pending = session.info.pop(PENDING, None)
    if not pending:
        return
    with _LOCK:
        for url, edits in pending.items():
            found = _WATCHED.get(url)
            if found is not None:
                found.update(edits)


@event.listens_for(Session, "after_rollback")
def drop_edits(session: Session) -> None:
    session.info.pop(PENDING, None)


def watching(session: Session) -> str | None:
    with _LOCK:
        if not _WATCHED:
            return None
    url = url_of(session)
    with _LOCK:
        return url if url in _WATCHED else None


def edit_of(table: str, row: Any) -> Edit | None:
    found = RECORD_KEYS.get(table)
    if found is None:
        return None
    column, kind = found
    state = instance_state(row)
    committed = state.committed_state.get(column)
    value = committed if isinstance(committed, int) else getattr(row, state.mapper.get_property_by_column(state.mapper.local_table.columns[column]).key)
    return (kind, value) if isinstance(value, int) and not isinstance(value, bool) else None


@event.listens_for(Session, "before_flush")
def note_flushed_edits(session: Session, _transaction: UOWTransaction, _instances: object) -> None:
    url = watching(session)
    if url is None:
        return
    edits: set[Edit] = set()
    for row in [*session.dirty, *session.deleted]:
        table = instance_state(row).mapper.local_table
        if isinstance(table, Table) and table.name in RECORD_KEYS and (found := edit_of(table.name, row)) is not None:
            edits.add(found)
    hold(session, url, edits)


@event.listens_for(Session, "do_orm_execute")
def note_statement_edits(state: ORMExecuteState) -> None:
    statement = state.statement
    if not isinstance(statement, Update | Delete):
        return
    table = statement.table
    if not isinstance(table, Table) or table.name not in RECORD_KEYS:
        return
    url = watching(state.session)
    if url is None:
        return
    column, kind = RECORD_KEYS[table.name]
    query = select(table.c[column])
    if statement.whereclause is not None:
        query = query.where(statement.whereclause)
    found = state.session.execute(query).scalars()
    hold(state.session, url, {(kind, value) for value in found if isinstance(value, int)})
