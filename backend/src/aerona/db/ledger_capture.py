import json
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Table, event, select, text, update
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session, UOWTransaction, object_mapper
from sqlalchemy.orm.base import instance_state

from aerona.constants.schema import LEDGER_SUMMARY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.tables.agency import ActionRecordRow, AgentTurnRow, TurnCounterRow
from aerona.db.tables.ledger import LedgerChangeRow, LedgerEntryRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind

RowKey = tuple[str, str]
RowValues = dict[str, Any]
LEDGER_TABLES = frozenset({LedgerEntryRow.__tablename__, LedgerChangeRow.__tablename__})
TURN_TABLES = frozenset({ActionRecordRow.__tablename__, AgentTurnRow.__tablename__, TurnCounterRow.__tablename__})


def jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(item) for item in value]
    return value


def key_text(values: RowValues) -> str:
    return json.dumps(values, sort_keys=True, default=str)


@dataclass(frozen=True)
class RowChange:
    table_name: str
    row_key: str
    operation: LedgerOperation
    before: RowValues | None
    after: RowValues | None


@dataclass(frozen=True)
class LedgerDraft:
    epoch: int
    actor_kind: ActorKind
    actor_node_id: int | None
    actor_name: str
    tool: str
    action_kind: ActionKind
    input_summary: str | None


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


def _raw_rows(connection: Connection, table: Table, where: str, params: dict[str, Any]) -> list[RowValues]:
    statement = text(f'SELECT * FROM "{table.name}" WHERE {where}')
    return [dict(row._mapping) for row in connection.execute(statement, params)]


def _pk_clause(table: Table) -> str:
    return " AND ".join(f'"{column.name}" = :{column.name}' for column in table.primary_key.columns)


def _pk_values(table: Table, row: RowValues) -> RowValues:
    return {column.name: row[column.name] for column in table.primary_key.columns}


@dataclass
class RowTracker:
    session: Session
    untracked: frozenset[str] = LEDGER_TABLES
    before: dict[RowKey, RowValues | None] = field(default_factory=dict)
    keys: dict[RowKey, RowValues] = field(default_factory=dict)
    insert_marks: dict[str, int] = field(default_factory=dict)

    def attach(self) -> None:
        event.listen(self.session, "before_flush", self._before_flush)
        event.listen(self.session, "after_flush", self._after_flush)
        event.listen(self.session, "do_orm_execute", self._on_execute)

    def detach(self) -> None:
        event.remove(self.session, "before_flush", self._before_flush)
        event.remove(self.session, "after_flush", self._after_flush)
        event.remove(self.session, "do_orm_execute", self._on_execute)

    def _remember(self, table: Table, pk: RowValues, before: RowValues | None) -> None:
        if table.name in self.untracked:
            return
        key = (table.name, key_text(pk))
        if key not in self.before:
            self.before[key] = before
            self.keys[key] = pk

    def _object_keys(self, instance: object) -> list[tuple[Table, RowValues]]:
        mapper = object_mapper(instance)
        known = instance_state(instance).identity
        identity = known if known is not None else mapper.primary_key_from_instance(instance)
        by_property = {mapper.get_property_by_column(column).key: value for column, value in zip(mapper.primary_key, identity, strict=True)}
        found: list[tuple[Table, RowValues]] = []
        for table in mapper.tables:
            if isinstance(table, Table):
                pk = {column.name: by_property.get(mapper.get_property_by_column(column).key) for column in table.primary_key.columns}
                if all(value is not None for value in pk.values()):
                    found.append((table, pk))
        return found

    def _snapshot_existing(self, instance: object) -> None:
        connection = self.session.connection()
        for table, pk in self._object_keys(instance):
            if table.name in self.untracked or (table.name, key_text(pk)) in self.before:
                continue
            rows = _raw_rows(connection, table, _pk_clause(table), pk)
            self._remember(table, pk, rows[0] if rows else None)

    def _before_flush(self, session: Session, context: UOWTransaction, instances: object) -> None:
        for instance in list(session.dirty):
            if session.is_modified(instance, include_collections=False):
                self._snapshot_existing(instance)
        for instance in list(session.deleted):
            self._snapshot_existing(instance)

    def _after_flush(self, session: Session, context: UOWTransaction) -> None:
        for instance in list(session.new):
            for table, pk in self._object_keys(instance):
                self._remember(table, pk, None)

    def _on_execute(self, state: ORMExecuteState) -> None:
        statement = state.statement
        target = getattr(statement, "table", None)
        if not isinstance(target, Table) or target.name in self.untracked:
            return
        connection = self.session.connection()
        if state.is_insert:
            if target.name not in self.insert_marks:
                mark = connection.execute(text(f'SELECT coalesce(max(rowid), 0) FROM "{target.name}"')).scalar_one()
                self.insert_marks[target.name] = int(mark)
            return
        if not (state.is_update or state.is_delete):
            return
        where = getattr(statement, "whereclause", None)
        query = select(*target.primary_key.columns)
        if where is not None:
            query = query.where(where)
        for keys in connection.execute(query):
            pk = dict(keys._mapping)
            if (target.name, key_text(pk)) in self.before:
                continue
            rows = _raw_rows(connection, target, _pk_clause(target), pk)
            if rows:
                self._remember(target, pk, None if self._inserted_here(connection, target, pk) else rows[0])

    def _inserted_here(self, connection: Connection, table: Table, pk: RowValues) -> bool:
        mark = self.insert_marks.get(table.name)
        if mark is None:
            return False
        rowid = connection.execute(text(f'SELECT rowid FROM "{table.name}" WHERE {_pk_clause(table)}'), pk).scalar_one_or_none()
        return rowid is not None and int(rowid) > mark

    def _collect_inserts(self, connection: Connection) -> None:
        for name, mark in self.insert_marks.items():
            table = _table(name)
            for row in _raw_rows(connection, table, "rowid > :mark", {"mark": mark}):
                self._remember(table, _pk_values(table, row), None)

    def changes(self, connection: Connection) -> list[RowChange]:
        self._collect_inserts(connection)
        found: list[RowChange] = []
        for key, before in self.before.items():
            name, row_key = key
            table = _table(name)
            rows = _raw_rows(connection, table, _pk_clause(table), self.keys[key])
            after = rows[0] if rows else None
            if before == after:
                continue
            operation = LedgerOperation.INSERT if before is None else LedgerOperation.DELETE if after is None else LedgerOperation.UPDATE
            found.append(RowChange(name, row_key, operation, jsonable(before), jsonable(after)))
        return found


def inserted_action_ids(changes: Iterable[RowChange]) -> list[int]:
    return [
        int(change.after["id"])
        for change in changes
        if change.table_name == ActionRecordRow.__tablename__ and change.operation is LedgerOperation.INSERT and change.after is not None
    ]


async def write_entry(session: AsyncSession, draft: LedgerDraft, changes: list[RowChange]) -> LedgerEntryRow:
    entry = LedgerEntryRow(
        epoch=draft.epoch,
        actor_kind=draft.actor_kind,
        actor_node_id=draft.actor_node_id,
        actor_name=draft.actor_name[:NAME_MAX_LENGTH],
        tool=draft.tool,
        action_kind=draft.action_kind,
        input_summary=draft.input_summary[:LEDGER_SUMMARY_MAX_LENGTH] if draft.input_summary else None,
        applied=[],
        conflicts=[],
    )
    session.add(entry)
    await session.flush()
    action_ids = inserted_action_ids(changes)
    if action_ids:
        await session.execute(update(ActionRecordRow).where(ActionRecordRow.id.in_(action_ids)).values(ledger_entry_id=entry.id))
    session.add_all(
        LedgerChangeRow(
            entry_id=entry.id,
            table_name=change.table_name,
            row_key=change.row_key,
            operation=change.operation,
            before=change.before,
            after={**change.after, "ledger_entry_id": entry.id}
            if change.after is not None and change.table_name == ActionRecordRow.__tablename__
            else change.after,
        )
        for change in changes
    )
    await session.flush()
    return entry


class ChangeCapture:
    def __init__(self, session: AsyncSession, untracked: frozenset[str] = LEDGER_TABLES) -> None:
        self._session = session
        self._tracker = RowTracker(session.sync_session, untracked)
        self._attached = False

    def start(self) -> None:
        if not self._attached:
            self._tracker.attach()
            self._attached = True

    def stop(self) -> None:
        if self._attached:
            self._tracker.detach()
            self._attached = False

    async def changes(self) -> list[RowChange]:
        await self._session.flush()
        self.stop()
        return await self._session.run_sync(lambda sync: self._tracker.changes(sync.connection()))

    async def seal(self, draft: LedgerDraft) -> int | None:
        changes = await self.changes()
        if not changes:
            return None
        return (await write_entry(self._session, draft, changes)).id


@asynccontextmanager
async def capture_changes(session: AsyncSession, untracked: frozenset[str] = LEDGER_TABLES) -> AsyncIterator[ChangeCapture]:
    await session.flush()
    capture = ChangeCapture(session, untracked)
    capture.start()
    try:
        yield capture
    finally:
        capture.stop()
