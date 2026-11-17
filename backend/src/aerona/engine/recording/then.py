import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.base import Base
from aerona.db.ledger_capture import jsonable, key_text, table_plan
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.node import NodeRow
from aerona.domain.models.moment import Moment
from aerona.engine.recording.checkpoints import captured_tables
from aerona.engine.recording.past import present_row, state_at

NODE_TABLES = frozenset({"nodes", "entities"})


@dataclass(frozen=True)
class FieldThen:
    field: str
    then: str | None
    now: str | None

    @property
    def changed(self) -> bool:
        return self.then != self.now


@dataclass(frozen=True)
class RowThen:
    table_name: str
    row_key: str
    existed: bool
    exists_now: bool
    fields: tuple[FieldThen, ...]


@dataclass(frozen=True)
class ThenPage:
    total: int
    rows: tuple[RowThen, ...]


def shown(value: Any) -> str | None:
    if value is None:
        return None
    plain = jsonable(value)
    return plain if isinstance(plain, str) else json.dumps(plain, sort_keys=True, default=str)


def node_keyed(table: Table) -> str | None:
    primary = list(table.primary_key.columns)
    if len(primary) != 1:
        return None
    column = primary[0]
    if table.name in NODE_TABLES:
        return column.name
    targets = {key.column.table.name for key in column.foreign_keys}
    return column.name if targets & NODE_TABLES else None


def node_tables() -> list[tuple[Table, str]]:
    found: list[tuple[Table, str]] = []
    for table in captured_tables():
        column = node_keyed(table)
        if column is not None:
            found.append((table, column))
    return found


async def row_then(session: AsyncSession, table: Table, key: Mapping[str, Any], *, epoch: int, moment: Moment | None) -> RowThen | None:
    then = await state_at(session, table.name, key, epoch=epoch, moment=moment)
    now = await present_row(session, table.name, key)
    if then is None and now is None:
        return None
    names = [column.name for column in table_plan(table).columns]
    fields = tuple(
        FieldThen(field=name, then=shown(then.get(name)) if then is not None else None, now=shown(now.get(name)) if now is not None else None) for name in names
    )
    return RowThen(table_name=table.name, row_key=key_text(dict(key)), existed=then is not None, exists_now=now is not None, fields=fields)


async def node_then(session: AsyncSession, node_id: int, *, epoch: int, moment: Moment | None = None) -> ThenPage:
    if await session.scalar(select(NodeRow.id).where(NodeRow.id == node_id)) is None:
        raise NotFoundError("No such record.")
    rows: list[RowThen] = []
    for table, column in node_tables():
        found = await row_then(session, table, {column: node_id}, epoch=epoch, moment=moment)
        if found is not None:
            rows.append(found)
    return ThenPage(total=len(rows), rows=tuple(rows))


def known_table(table_name: str) -> Table:
    table = Base.metadata.tables.get(table_name)
    if table is None or table not in captured_tables():
        raise ValidationFailedError(f"The past of {table_name} is not kept.")
    return table


async def table_keys(session: AsyncSession, table: Table) -> list[str]:
    primary = list(table.primary_key.columns)
    present = await session.execute(select(*primary))
    keys = {key_text({column.name: jsonable(value) for column, value in zip(primary, row, strict=True)}) for row in present}
    changed = await session.scalars(select(StateChangeRow.row_key).where(StateChangeRow.table_name == table.name).distinct())
    keys.update(changed)
    return sorted(keys)


async def table_then(
    session: AsyncSession, table_name: str, *, epoch: int, moment: Moment | None = None, key: Mapping[str, Any] | None = None, offset: int = 0, limit: int = 50
) -> ThenPage:
    table = known_table(table_name)
    if key is not None:
        found = await row_then(session, table, key, epoch=epoch, moment=moment)
        return ThenPage(total=1 if found is not None else 0, rows=(found,) if found is not None else ())
    keys = await table_keys(session, table)
    rows: list[RowThen] = []
    for row_key in keys[offset : offset + limit]:
        found = await row_then(session, table, json.loads(row_key), epoch=epoch, moment=moment)
        if found is not None:
            rows.append(found)
    return ThenPage(total=len(keys), rows=tuple(rows))
