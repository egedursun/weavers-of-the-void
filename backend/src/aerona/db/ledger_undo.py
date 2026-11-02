import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Table, delete, select, text
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import instance_state

from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.base import Base
from aerona.db.ledger_capture import key_text
from aerona.db.ledger_rows import (
    BIRTH_COST_COLUMNS,
    IDENTITY_COLUMNS,
    IGNORED_COLUMNS,
    MERGEABLE_JSON_COLUMNS,
    PERMANENT_BIRTH_TABLES,
    QUANTITY_COLUMNS,
    WHITELISTED_TABLES,
    Change,
    RowValues,
    delta_undo,
    is_number,
    merge_json,
    parse_json,
    to_change,
)
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.ledger import LedgerChangeRow, LedgerEntryRow
from aerona.db.tables.meta import NotificationRow
from aerona.domain.enums.bond import BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.meta import LedgerOperation

COMPANION_INSERT_TABLES = frozenset({"nodes"})
KEEP = object()


@dataclass
class UndoReport:
    applied: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


def _table(name: str) -> Table:
    table = Base.metadata.tables.get(name)
    if table is None:
        raise ConflictError(f"Unknown table {name}.")
    return table


def _where(table: Table, key: RowValues) -> tuple[str, dict[str, Any]]:
    columns = [column.name for column in table.primary_key.columns]
    clause = " AND ".join(f'"{column}" = :key_{column}' for column in columns)
    return clause, {f"key_{column}": key.get(column) for column in columns}


async def current_row(session: AsyncSession, table_name: str, key: RowValues) -> RowValues | None:
    table = _table(table_name)
    clause, params = _where(table, key)
    result = await session.execute(text(f'SELECT * FROM "{table.name}" WHERE {clause}'), params)
    row = result.mappings().first()
    return dict(row) if row is not None else None


async def _update_columns(session: AsyncSession, table_name: str, key: RowValues, values: RowValues) -> None:
    table = _table(table_name)
    known = {column.name for column in table.columns}
    assignments = {column: value for column, value in values.items() if column in known}
    if not assignments:
        return
    clause, params = _where(table, key)
    setters = ", ".join(f'"{column}" = :value_{column}' for column in assignments)
    params.update({f"value_{column}": value for column, value in assignments.items()})
    await session.execute(text(f'UPDATE "{table.name}" SET {setters} WHERE {clause}'), params)


async def _insert_row(session: AsyncSession, table_name: str, values: RowValues) -> None:
    table = _table(table_name)
    known = [column.name for column in table.columns if column.name in values]
    columns = ", ".join(f'"{column}"' for column in known)
    placeholders = ", ".join(f":value_{column}" for column in known)
    await session.execute(text(f'INSERT INTO "{table.name}" ({columns}) VALUES ({placeholders})'), {f"value_{column}": values[column] for column in known})


async def _delete_row(session: AsyncSession, table_name: str, key: RowValues) -> None:
    table = _table(table_name)
    clause, params = _where(table, key)
    await session.execute(text(f'DELETE FROM "{table.name}" WHERE {clause}'), params)


def _replaced(current: RowValues, after: RowValues) -> bool:
    return any(column in current and column in after and current[column] != after[column] for column in IDENTITY_COLUMNS)


class UndoRun:
    def __init__(self, session: AsyncSession, epoch: int, changes: list[Change], names: dict[str, str]) -> None:
        self.session = session
        self.epoch = epoch
        self.changes = changes
        self.names = names
        self.report = UndoReport()
        self.inserted = {(change.table, json.dumps(change.key, sort_keys=True)) for change in changes if change.operation is LedgerOperation.INSERT}
        self.born: set[tuple[str, str]] = set()

    def name(self, change: Change) -> str:
        return self.names.get(change.label_key, f"#{change.row_id}" if change.row_id is not None else change.table)

    async def prepare(self) -> None:
        for change in self.changes:
            permanent = change.operation is LedgerOperation.INSERT and change.table in PERMANENT_BIRTH_TABLES
            if permanent and await current_row(self.session, change.table, change.key) is not None:
                self.born.add((change.table, json.dumps(change.key, sort_keys=True)))

    async def run(self) -> UndoReport:
        await self.prepare()
        for change in sorted(self.changes, key=lambda item: item.id, reverse=True):
            if change.table not in WHITELISTED_TABLES:
                continue
            try:
                async with self.session.begin_nested():
                    await self._undo(change)
                    await self.session.flush()
            except Exception as error:
                self.report.conflicts.append(f"{self.name(change)} ({change.table}) could not be undone: {error}")
        await self._refresh_touched()
        return self.report

    async def _refresh_touched(self) -> None:
        touched = {(change.table, json.dumps(change.key, sort_keys=True)) for change in self.changes}
        for instance in list(self.session.identity_map.values()):
            state = instance_state(instance)
            identity = state.identity
            if identity is None or state.deleted or state.detached:
                continue
            for table in state.mapper.tables:
                if not isinstance(table, Table):
                    continue
                key = {column.name: value for column, value in zip(table.primary_key.columns, identity, strict=False)}
                if (table.name, json.dumps(key, sort_keys=True)) in touched:
                    try:
                        await self.session.refresh(instance)
                    except InvalidRequestError:
                        self.session.expunge(instance)
                    break

    async def _undo(self, change: Change) -> None:
        if change.operation is LedgerOperation.INSERT:
            await self._undo_insert(change)
        elif change.operation is LedgerOperation.DELETE:
            await self._undo_delete(change)
        else:
            await self._undo_update(change)

    async def _undo_insert(self, change: Change) -> None:
        if change.table in COMPANION_INSERT_TABLES:
            return
        current = await current_row(self.session, change.table, change.key)
        if current is None:
            return
        name = self.name(change)
        if change.after is not None and _replaced(current, change.after):
            self.report.conflicts.append(f"{name} was later deleted and replaced by another record; left untouched.")
            return
        if change.table in PERMANENT_BIRTH_TABLES:
            self.report.conflicts.append(f"{name} was not deleted (a born being cannot be undone); its birth cost is not refunded either.")
            return
        row_id = change.row_id
        if change.table == "entities" and row_id is not None:
            entity = await self.session.get(EntityRow, row_id, populate_existing=True)
            if entity is not None and entity.status is not EntityStatus.REJECTED:
                await EntityRepository(self.session).set_status(entity, EntityStatus.REJECTED, self.epoch)
            self.report.applied.append(f"{name} rejected")
            return
        if change.table == "bonds" and row_id is not None:
            bond = await self.session.get(BondRow, row_id, populate_existing=True)
            if bond is not None and bond.state is BondState.ACTIVE:
                await BondRepository(self.session).deactivate(bond, self.epoch)
            self.report.applied.append(f"{name} closed")
            return
        if change.table == "chronicle" and row_id is not None:
            await self.session.execute(delete(NotificationRow).where(NotificationRow.chronicle_id == row_id))
        await _delete_row(self.session, change.table, change.key)
        self.report.applied.append(f"{name} removed")

    async def _undo_delete(self, change: Change) -> None:
        if change.before is None:
            return
        name = self.name(change)
        current = await current_row(self.session, change.table, change.key)
        if current is not None:
            if all(current.get(column) == value for column, value in change.before.items() if column not in IGNORED_COLUMNS):
                return
            if "id" in change.key:
                self.report.conflicts.append(f"{name} could not be rewritten: its number (#{change.key['id']}) passed to another record.")
            else:
                self.report.conflicts.append(f"{name}: a new record with the same key is in its place.")
            return
        await _insert_row(self.session, change.table, change.before)
        self.report.applied.append(f"{name} restored")

    def _restored_value(self, change: Change, column: str, now: Any, name: str) -> Any:
        before = (change.before or {}).get(column)
        after = (change.after or {}).get(column)
        if self.born and column in BIRTH_COST_COLUMNS.get(change.table, frozenset()) and is_number(before) and is_number(after) and after < before:
            self.report.conflicts.append(f"{name} \u00b7 {column} cost ({after - before}) not refunded: the born record is permanent.")
            return KEEP
        if now == after:
            return before
        if column in QUANTITY_COLUMNS and is_number(now) and is_number(before) and is_number(after):
            return type(now)(delta_undo(now, before, after))
        if column in MERGEABLE_JSON_COLUMNS:
            merged, ok = merge_json(parse_json(now), parse_json(before), parse_json(after))
            if ok:
                return json.dumps(merged)
        self.report.conflicts.append(f"{name} \u00b7 {column} changed later, left as is.")
        return KEEP

    async def _undo_update(self, change: Change) -> None:
        identity = (change.table, json.dumps(change.key, sort_keys=True))
        if identity in self.inserted or identity in self.born or change.before is None or change.after is None:
            return
        name = self.name(change)
        current = await current_row(self.session, change.table, change.key)
        if current is None:
            self.report.conflicts.append(f"{name} no longer exists.")
            return
        restored: RowValues = {}
        for column in change.diff_columns():
            if column in current:
                value = self._restored_value(change, column, current[column], name)
                if value is not KEEP:
                    restored[column] = value
        if not restored:
            return
        renamed = False
        if change.table == "nodes" and "name" in restored and change.row_id is not None:
            await NameRepository(self.session).rename(change.row_id, str(restored.pop("name")))
            renamed = True
        await _update_columns(self.session, change.table, change.key, restored)
        columns = sorted(set(restored) | ({"name"} if renamed else set()))
        self.report.applied.append(f"{name}: {', '.join(columns)} restored")


async def changes_of(session: AsyncSession, entry_id: int) -> list[Change]:
    rows = await session.scalars(select(LedgerChangeRow).where(LedgerChangeRow.entry_id == entry_id).order_by(LedgerChangeRow.id))
    return [to_change(row) for row in rows]


async def creating_entry_id(session: AsyncSession, entity_id: int) -> int | None:
    statement = (
        select(LedgerEntryRow.id)
        .join(LedgerChangeRow, LedgerChangeRow.entry_id == LedgerEntryRow.id)
        .where(
            LedgerChangeRow.table_name == EntityRow.__tablename__,
            LedgerChangeRow.row_key == key_text({"id": entity_id}),
            LedgerChangeRow.operation == LedgerOperation.INSERT,
            LedgerEntryRow.undone.is_(False),
        )
        .order_by(LedgerEntryRow.id.desc())
        .limit(1)
    )
    found = await session.scalar(statement)
    return int(found) if found is not None else None


async def undo_entry(session: AsyncSession, entry_id: int, epoch: int, names: dict[str, str] | None = None) -> UndoReport:
    entry = await session.get(LedgerEntryRow, entry_id)
    if entry is None:
        raise NotFoundError("No such entry in the ledger.")
    if entry.undone:
        raise ConflictError("This entry was already undone.")
    report = await UndoRun(session, epoch, await changes_of(session, entry_id), names or {}).run()
    entry = await session.get(LedgerEntryRow, entry_id, populate_existing=True)
    if entry is None:
        raise NotFoundError("No such entry in the ledger.")
    entry.undone = True
    entry.undone_at = datetime.now(UTC)
    entry.applied = report.applied
    entry.conflicts = report.conflicts
    await session.flush()
    return report
