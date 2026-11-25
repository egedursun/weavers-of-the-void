from collections.abc import AsyncGenerator, Awaitable, Callable, Iterable, Sequence
from typing import Any

from sqlalchemy import Select, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper
from sqlalchemy.sql.elements import KeyedColumnElement

from aerona.core.grammar import spoken
from aerona.db.base import Base
from aerona.db.profile_guard import LOCK_COLUMN, table_name
from aerona.db.tables.ledger import LedgerChangeRow
from aerona.db.tables.node import NodeRow
from aerona.tools.divine_will.paging import plain

NODE_TARGETS = frozenset({"nodes", "entities", "sons", "worlds", "stars", "foreign_gods", "creator", "galaxies", "galaxy_clusters", "dimensions"})
NODE_SUFFIXES = ("_node_id", "_entity_id")
CHUNK = 500
OWN_ID = "id"


def mapper_of(table: str) -> Mapper[Any] | None:
    return next((mapper for mapper in Base.registry.mappers if table_name(mapper) == table), None)


def every_table() -> list[Mapper[Any]]:
    return sorted(Base.registry.mappers, key=table_name)


def points_at_node(column: KeyedColumnElement[Any]) -> bool:
    return any(foreign.column.table.name in NODE_TARGETS for foreign in column.foreign_keys) or column.key.endswith(NODE_SUFFIXES)


def is_long_text(column: KeyedColumnElement[Any]) -> bool:
    return isinstance(column.type, Text)


def keys_of(mapper: Mapper[Any]) -> list[str]:
    return [mapper.get_property_by_column(column).key for column in mapper.primary_key]


def attributes(mapper: Mapper[Any]) -> list[tuple[str, KeyedColumnElement[Any]]]:
    return [(attribute.key, attribute.columns[0]) for attribute in mapper.column_attrs if attribute.key != LOCK_COLUMN]


def node_ids(mapper: Mapper[Any], rows: Iterable[Any]) -> set[int]:
    linked = [key for key, column in attributes(mapper) if points_at_node(column)]
    return {value for row in rows for key in linked if isinstance(value := getattr(row, key), int) and not isinstance(value, bool)}


async def names_for(session: AsyncSession, ids: Iterable[int]) -> dict[int, str]:
    wanted = sorted(set(ids))
    found: dict[int, str] = {}
    for start in range(0, len(wanted), CHUNK):
        chunk = wanted[start : start + CHUNK]
        found.update({node_id: name for node_id, name in await session.execute(select(NodeRow.id, NodeRow.name).where(NodeRow.id.in_(chunk)))})
    return found


def shown(column: KeyedColumnElement[Any], value: Any, names: dict[int, str]) -> str:
    if points_at_node(column) and column.key != OWN_ID and isinstance(value, int) and not isinstance(value, bool):
        named = names.get(value)
        return f"{named} (node {value})" if named else f"node {value}"
    return plain(value)


def row_line(mapper: Mapper[Any], row: Any, names: dict[int, str], *, skip: frozenset[str] = frozenset()) -> str:
    parts = [f"{key}: {shown(column, value, names)}" for key, column in attributes(mapper) if key not in skip and (value := getattr(row, key)) is not None]
    return " · ".join(parts)


async def rendered_rows(session: AsyncSession, mapper: Mapper[Any], rows: Sequence[Any]) -> list[str]:
    names = await names_for(session, node_ids(mapper, rows))
    return [row_line(mapper, row, names) for row in rows]


async def streamed(session: AsyncSession, statement: Select[Any], render: Callable[[Sequence[Any]], Awaitable[list[str]]]) -> AsyncGenerator[str]:
    offset = 0
    while True:
        chunk = list(await session.scalars(statement.offset(offset).limit(CHUNK)))
        if not chunk:
            return
        for line in await render(chunk):
            yield line
        if len(chunk) < CHUNK:
            return
        offset += CHUNK


def change_text(change: LedgerChangeRow) -> str:
    before, after = change.before or {}, change.after or {}
    head = f"  - {spoken(change.operation)} {change.table_name} {change.row_key}"
    if before and after:
        moved = [f"{key}: {plain(before.get(key))} -> {plain(after.get(key))}" for key in sorted({*before, *after}) if before.get(key) != after.get(key)]
        return head + (f" · {'; '.join(moved)}" if moved else "")
    shown_values = after or before
    return head + (f" · {'; '.join(f'{key}: {plain(value)}' for key, value in sorted(shown_values.items()) if value is not None)}" if shown_values else "")
