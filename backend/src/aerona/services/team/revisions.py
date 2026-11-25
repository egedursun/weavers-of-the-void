from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, and_, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.account_scope import AccountRef
from aerona.core.errors import EditConflictError
from aerona.db.tables.changes import StateChangeRow

CONFLICT_TEXT = "Someone else changed this since you opened it."

type ChangeValue = float | int | str | None


@dataclass(frozen=True)
class Revision:
    revision: int
    changed_by: str | None
    changed_at: datetime | None


@dataclass(frozen=True)
class ConflictChange:
    table: str
    node_id: int | None
    field: str | None
    before: ChangeValue
    after: ChangeValue
    by: str | None
    by_account_id: int | None
    at: datetime | None


async def latest_revision(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)


async def node_revision(session: AsyncSession, node_id: int) -> Revision:
    latest = await session.scalar(select(func.max(StateChangeRow.id)).where(StateChangeRow.node_id == node_id))
    if latest is None:
        return Revision(0, None, None)
    person = await session.scalar(
        select(StateChangeRow)
        .where(StateChangeRow.node_id == node_id, StateChangeRow.author_account_id.is_not(None))
        .order_by(StateChangeRow.id.desc())
        .limit(1)
    )
    if person is None:
        return Revision(int(latest), None, None)
    return Revision(int(latest), person.author_name, person.changed_at)


def before_value(row: StateChangeRow) -> ChangeValue:
    if row.before_node_id is not None:
        return row.before_node_id
    return row.before_number if row.before_number is not None else row.before_text


def after_value(row: StateChangeRow) -> ChangeValue:
    if row.after_node_id is not None:
        return row.after_node_id
    return row.after_number if row.after_number is not None else row.after_text


def by_others(author: AccountRef | None) -> ColumnElement[bool]:
    others = StateChangeRow.author_account_id.is_not(None)
    return others if author is None else and_(others, StateChangeRow.author_account_id != author.id)


def touches(mine: list[StateChangeRow], theirs: StateChangeRow) -> bool:
    for row in mine:
        if row.table_name != theirs.table_name or row.row_key != theirs.row_key:
            continue
        if row.field is None or theirs.field is None or row.field == theirs.field:
            return True
    return False


async def conflicts_since(session: AsyncSession, expected: int, mine_from: int, author: AccountRef | None) -> list[ConflictChange]:
    if expected >= mine_from:
        return []
    mine = list(await session.scalars(select(StateChangeRow).where(StateChangeRow.id > mine_from).order_by(StateChangeRow.id)))
    keys = sorted({(row.table_name, row.row_key) for row in mine})
    if not keys:
        return []
    candidates = await session.scalars(
        select(StateChangeRow)
        .where(
            StateChangeRow.id > expected,
            StateChangeRow.id <= mine_from,
            tuple_(StateChangeRow.table_name, StateChangeRow.row_key).in_(keys),
            by_others(author),
        )
        .order_by(StateChangeRow.id)
    )
    grouped: dict[tuple[str, str, str | None], list[StateChangeRow]] = {}
    for row in candidates:
        if touches(mine, row):
            grouped.setdefault((row.table_name, row.row_key, row.field), []).append(row)
    found: list[ConflictChange] = []
    for (table, _key, field), rows in grouped.items():
        first, last = rows[0], rows[-1]
        found.append(
            ConflictChange(table, last.node_id, field, before_value(first), after_value(last), last.author_name, last.author_account_id, last.changed_at)
        )
    return found


def conflict_payload(changes: list[ConflictChange]) -> list[dict[str, object]]:
    return [
        {
            "table": change.table,
            "node_id": change.node_id,
            "field": change.field,
            "before": change.before,
            "after": change.after,
            "by": change.by,
            "by_account_id": change.by_account_id,
            "at": change.at.isoformat() if change.at is not None else None,
        }
        for change in changes
    ]


async def refuse_conflicts(session: AsyncSession, expected: int | None, mine_from: int, author: AccountRef | None) -> None:
    if expected is None:
        return
    found = await conflicts_since(session, expected, mine_from, author)
    if found:
        raise EditConflictError(CONFLICT_TEXT, conflict_payload(found))
