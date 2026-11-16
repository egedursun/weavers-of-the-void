from collections.abc import Callable
from typing import Any

from sqlalchemy import Integer, Table, UniqueConstraint, delete, func, inspect, or_, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from aerona.db.base import Base
from aerona.db.profile_guard import NODE_TABLES

Touched = dict[str, set[tuple[Any, ...]]]


def keyed_by_epoch(table: Table) -> list[str]:
    keys = [list(table.primary_key.columns)]
    keys += [list(constraint.columns) for constraint in table.constraints if isinstance(constraint, UniqueConstraint)]
    keys += [list(index.columns) for index in table.indexes if index.unique]
    return [column.name for columns in keys for column in columns if "epoch" in column.name and len(columns) > 1]


def node_columns(table: Table) -> list[str]:
    return [column.name for column in table.columns if any(foreign.column.table.name in NODE_TABLES for foreign in column.foreign_keys)]


def epoch_columns(table: Table) -> list[str]:
    return [column.name for column in table.columns if "epoch" in column.name and isinstance(column.type, Integer)]


def epoch_points() -> list[tuple[Table, str, list[str]]]:
    found: list[tuple[Table, str, list[str]]] = []
    for table in Base.metadata.sorted_tables:
        epochs, nodes = keyed_by_epoch(table), node_columns(table)
        if epochs and nodes:
            found.append((table, epochs[0], nodes))
    return found


def epoch_logs() -> list[tuple[Table, str]]:
    return [
        (table, next(column.name for column in table.primary_key.columns if "epoch" in column.name))
        for table in Base.metadata.sorted_tables
        if not node_columns(table) and any("epoch" in column.name for column in table.primary_key.columns)
    ]


def loose_tables() -> dict[str, Table]:
    logs = {table.name for table, _ in epoch_logs()}
    return {table.name: table for table in Base.metadata.sorted_tables if epoch_columns(table) and not node_columns(table) and table.name not in logs}


def mapped(table: Table) -> type[Any] | Table:
    return next((mapper.class_ for mapper in Base.registry.mappers if mapper.local_table is table), table)


def follow_touched(touched: Touched) -> Callable[..., None]:
    loose = loose_tables()

    def follow(sync: Session, *_: object) -> None:
        for row in [*sync.new, *sync.dirty]:
            table = getattr(row, "__table__", None)
            if table is not None and table.name in loose:
                identity = inspect(row).identity
                if identity is not None:
                    touched.setdefault(table.name, set()).add(tuple(identity))

    return follow


def turned_back(table: Table, column: str, birth: int, shift: int) -> Any:
    return func.max(birth, table.c[column] - shift)


async def rewind(session: AsyncSession, birth: int, last: int, inside: set[int], touched: Touched) -> int:
    shift = last - birth + 1
    own = sorted(inside)
    moved = 0
    points = {table.name: column for table, column, _ in epoch_points()}
    for table in Base.metadata.sorted_tables:
        nodes, epochs = node_columns(table), epoch_columns(table)
        if not nodes or not epochs:
            continue
        touching = or_(*(table.c[name].in_(own) for name in nodes))
        if table.name in points:
            key = points[table.name]
            await session.execute(delete(mapped(table)).where(touching, table.c[key] > birth, table.c[key] < last))
        for column in epochs:
            result = await session.execute(
                update(table)
                .where(touching, table.c[column] > birth)
                .values({column: turned_back(table, column, birth, shift)})
                .execution_options(synchronize_session=False)
            )
            moved += int(getattr(result, "rowcount", 0) or 0)
    for table, column in epoch_logs():
        await session.execute(delete(table).where(table.c[column] > birth))
    loose = loose_tables()
    for name, identities in sorted(touched.items()):
        table = loose[name]
        keys = list(table.primary_key.columns)
        for column in epoch_columns(table):
            for chunk in [sorted(identities)[index : index + 500] for index in range(0, len(identities), 500)]:
                result = await session.execute(
                    update(table)
                    .where(tuple_(*keys).in_(chunk), table.c[column] > birth)
                    .values({column: turned_back(table, column, birth, shift)})
                    .execution_options(synchronize_session=False)
                )
                moved += int(getattr(result, "rowcount", 0) or 0)
    session.expire_all()
    return moved
