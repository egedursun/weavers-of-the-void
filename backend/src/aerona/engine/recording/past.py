import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.base import Base
from aerona.db.ledger_capture import TablePlan, ValueKind, jsonable, key_text, table_plan
from aerona.db.tables.changes import StateChangeRow
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.models.moment import Moment

LATE = (10**9, 10**9, 10**9, 10**9)


@dataclass(frozen=True)
class Point:
    epoch: int
    moment: Moment | None = None
    until_change_id: int | None = None

    def key(self) -> tuple[int, tuple[int, int, int, int]]:
        return (self.epoch, self.moment.key() if self.moment is not None else LATE)

    def settled(self, row: StateChangeRow) -> bool:
        if self.until_change_id is not None:
            return row.id <= self.until_change_id
        return change_key(row)[0] <= self.key()


def change_key(row: StateChangeRow) -> tuple[tuple[int, tuple[int, int, int, int]], int]:
    moment = Moment(row.year, row.season, row.day, row.hour).key() if row.year is not None else LATE
    return ((row.epoch, moment), row.id)


def python_type_of(table_name: str, field: str) -> type:
    try:
        found: type = Base.metadata.tables[table_name].columns[field].type.python_type
    except NotImplementedError:
        return object
    return found


def decode_number(table_name: str, field: str, number: float | None) -> Any:
    if number is None:
        return None
    python_type = python_type_of(table_name, field)
    return python_type(number) if python_type in (int, bool) else number


def decode_text(table_name: str, field: str, text_value: str | None) -> Any:
    if text_value is None or python_type_of(table_name, field) is str:
        return text_value
    try:
        return json.loads(text_value)
    except ValueError:
        return text_value


def decode(plan: TablePlan, field: str, number: float | None, text_value: str | None, node: int | None) -> Any:
    column = plan.column(field)
    if column is not None and column.kind is ValueKind.NODE:
        return node
    if column is not None and column.kind is ValueKind.NUMBER:
        return decode_number(plan.name, field, number)
    return decode_text(plan.name, field, text_value)


def whole(text_value: str | None) -> dict[str, Any] | None:
    return json.loads(text_value) if text_value else None


async def present_row(session: AsyncSession, table_name: str, row_key: Mapping[str, Any]) -> dict[str, Any] | None:
    table = Base.metadata.tables[table_name]
    statement = select(table).where(*(table.columns[name] == value for name, value in row_key.items()))
    rows = (await session.execute(statement)).mappings().all()
    return {name: jsonable(value) for name, value in rows[0].items()} if rows else None


async def changes_of(session: AsyncSession, table_name: str, row_key: Mapping[str, Any]) -> list[StateChangeRow]:
    statement = select(StateChangeRow).where(StateChangeRow.table_name == table_name, StateChangeRow.row_key == key_text(dict(row_key)))
    return sorted(await session.scalars(statement), key=change_key)


def exists_at(changes: Sequence[StateChangeRow], point: Point, now: dict[str, Any] | None) -> tuple[bool, dict[str, Any] | None]:
    shaping = [row for row in changes if row.operation is not LedgerOperation.UPDATE]
    later_delete = next((row for row in shaping if not point.settled(row) and row.operation is LedgerOperation.DELETE), None)
    shape = whole(later_delete.before_text) if later_delete is not None else None
    before = [row for row in shaping if point.settled(row)]
    if before:
        last = before[-1]
        return (last.operation is LedgerOperation.INSERT, shape or whole(last.after_text))
    after = [row for row in shaping if not point.settled(row)]
    if after:
        return (after[0].operation is LedgerOperation.DELETE, shape)
    return (now is not None, None)


async def state_at(
    session: AsyncSession,
    table_name: str,
    row_key: Mapping[str, Any],
    *,
    epoch: int,
    moment: Moment | None = None,
    until_change_id: int | None = None,
) -> dict[str, Any] | None:
    point = Point(epoch, moment, until_change_id)
    plan = table_plan(Base.metadata.tables[table_name])
    now = await present_row(session, table_name, row_key)
    changes = await changes_of(session, table_name, row_key)
    alive, shape = exists_at(changes, point, now)
    if not alive:
        return None
    row = dict(now if now is not None else shape or {})
    for name in {column.name for column in plan.columns}:
        updates = [change for change in changes if change.operation is LedgerOperation.UPDATE and change.field == name]
        if not updates:
            continue
        settled = [change for change in updates if point.settled(change)]
        if settled:
            last = settled[-1]
            row[name] = decode(plan, name, last.after_number, last.after_text, last.after_node_id)
        else:
            first = updates[0]
            row[name] = decode(plan, name, first.before_number, first.before_text, first.before_node_id)
    return row


async def value_at(session: AsyncSession, table_name: str, row_key: Mapping[str, Any], field: str, *, epoch: int, moment: Moment | None = None) -> Any:
    row = await state_at(session, table_name, row_key, epoch=epoch, moment=moment)
    return row.get(field) if row is not None else None
