from pathlib import Path
from typing import Any

from sqlalchemy import Table, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.base import Base
from aerona.db.ledger_capture import UNCAPTURED_TABLES, Dependent, dependents_of, key_text
from aerona.db.profile_guard import table_name
from aerona.db.tables.changes import StateChangeRow
from aerona.domain.enums.meta import LedgerOperation
from tests.conftest import OpenDatabase
from tests.engine.core.stirring import stir
from tests.engine.integration.factories import seed_rich_cosmos

LEAST_RELATIONS = 40
Rows = dict[str, dict[str, dict[str, Any]]]


def keyed(table: Table, row: dict[str, Any]) -> str:
    return key_text({column.name: row[column.name] for column in table.primary_key.columns})


async def snapshot(session: AsyncSession) -> Rows:
    found: Rows = {}
    for table in Base.metadata.sorted_tables:
        if table.name in UNCAPTURED_TABLES:
            continue
        rows = [dict(row._mapping) for row in await session.execute(select(table))]
        found[table.name] = {keyed(table, row): row for row in rows}
    return found


async def parent_of(session: AsyncSession, parent: Table, dependent: Dependent) -> dict[str, Any] | None:
    child = dependent.table
    present = [child.c[name].is_not(None) for name in dependent.columns]
    found = (await session.execute(select(*(child.c[name] for name in dependent.columns)).where(*present).limit(1))).first()
    if found is None:
        return None
    match = [parent.c[name] == value for name, value in zip(dependent.referred, found, strict=True)]
    row = (await session.execute(select(parent).where(*match).limit(1))).first()
    return dict(row._mapping) if row is not None else None


async def remove(session: AsyncSession, parent: Table, row: dict[str, Any], by_statement: bool) -> bool:
    key = [parent.c[column.name] == row[column.name] for column in parent.primary_key.columns]
    mapper = next((item for item in Base.registry.mappers if parent in item.tables), None)
    try:
        async with session.begin_nested():
            if by_statement or mapper is None or table_name(mapper) != parent.name:
                await session.execute(delete(parent).where(*key))
            else:
                identity = tuple(row[column.name] for column in mapper.primary_key)
                instance = await session.get(mapper.class_, identity if len(identity) > 1 else identity[0])
                if instance is None:
                    return False
                await session.delete(instance)
                await session.flush()
    except IntegrityError:
        return False
    return True


def missing_records(before: Rows, after: Rows, recorded: set[tuple[str, str, str | None, str]]) -> list[str]:
    gaps: list[str] = []
    for table in Base.metadata.sorted_tables:
        if table.name in UNCAPTURED_TABLES:
            continue
        old, new = before.get(table.name, {}), after.get(table.name, {})
        gaps.extend(
            f"{table.name} {key} deleted" for key in sorted(old) if key not in new and (table.name, key, None, LedgerOperation.DELETE.value) not in recorded
        )
        for key in sorted(set(old) & set(new)):
            for column in sorted(name for name, value in old[key].items() if value is not None and new[key].get(name) is None):
                if (table.name, key, column, LedgerOperation.UPDATE.value) not in recorded:
                    gaps.append(f"{table.name} {key} {column} set to nothing")
    return gaps


async def test_every_row_a_delete_takes_with_it_reaches_the_change_record(tmp_path: Path, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "world.db")
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    exercised: set[tuple[str, str, tuple[str, ...]]] = set()
    async with database.write() as session:
        mark = int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)
        before = await snapshot(session)
        turn = 0
        for parent in Base.metadata.sorted_tables:
            for dependent in dependents_of(parent.name):
                row = await parent_of(session, parent, dependent)
                if row is None:
                    continue
                turn += 1
                if await remove(session, parent, row, by_statement=turn % 2 == 0):
                    exercised.add((parent.name, dependent.table.name, dependent.columns))
        await session.flush()
        after = await snapshot(session)
        recorded = {
            (table, row_key, column, operation.value)
            for table, row_key, column, operation in await session.execute(
                select(StateChangeRow.table_name, StateChangeRow.row_key, StateChangeRow.field, StateChangeRow.operation).where(StateChangeRow.id > mark)
            )
        }
        recorded |= {(table, row_key, None, operation) for table, row_key, column, operation in recorded if operation == LedgerOperation.DELETE.value}
        await session.rollback()
    gaps = missing_records(before, after, recorded)
    assert len(exercised) >= LEAST_RELATIONS, sorted(exercised)
    assert gaps[:20] == [], len(gaps)
    await database.dispose()
