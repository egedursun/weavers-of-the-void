from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session

READ_ONLY_KEY = "read_only"


class ReadSessionWriteError(RuntimeError):
    pass


def refuse_flush(session: Session, *_: object) -> None:
    if not session.info.get(READ_ONLY_KEY):
        return
    changed = session.new or session.deleted or any(session.is_modified(row) for row in session.dirty)
    if changed:
        raise ReadSessionWriteError("A read session tried to write; writes must go through Database.write so they hold the write lock.")


def refuse_statement(state: ORMExecuteState) -> None:
    if state.session.info.get(READ_ONLY_KEY) and (state.is_insert or state.is_update or state.is_delete):
        raise ReadSessionWriteError("A read session tried to write; writes must go through Database.write so they hold the write lock.")


def mark_read_only(session: Any) -> None:
    session.sync_session.info[READ_ONLY_KEY] = True


def install_read_only_guard() -> None:
    if not event.contains(Session, "before_flush", refuse_flush):
        event.listen(Session, "before_flush", refuse_flush)
    if not event.contains(Session, "do_orm_execute", refuse_statement):
        event.listen(Session, "do_orm_execute", refuse_statement)
