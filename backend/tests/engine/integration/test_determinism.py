import hashlib
import time
from pathlib import Path

from sqlalchemy import Float, select
from sqlalchemy.sql.schema import Table

from aerona.db.base import Base
from aerona.db.session import Database
from aerona.db.types import UtcDateTime
from aerona.engine.pipeline import current_environment, run_epoch_transition, run_tick, simulate
from aerona.rules.registry import Rules
from tests.conftest import OpenDatabase
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 20
TIMING_COLUMNS = frozenset({"seconds", "elapsed_seconds", "duration_seconds", "phase_seconds"})


def stable_columns(table: Table) -> list[str]:
    return [
        column.name
        for column in table.columns
        if not isinstance(column.type, UtcDateTime) and column.name not in TIMING_COLUMNS and not (isinstance(column.type, Float) and "second" in column.name)
    ]


async def table_digests(database: Database) -> dict[str, str]:
    digests: dict[str, str] = {}
    async with database.read() as session:
        for table in Base.metadata.sorted_tables:
            columns = stable_columns(table)
            order = [table.c[name] for name in columns]
            rows = await session.execute(select(*(table.c[name] for name in columns)).order_by(*order))
            digest = hashlib.sha256()
            for row in rows:
                digest.update(repr(tuple(row)).encode())
            digests[table.name] = digest.hexdigest()
    return digests


async def seeded_run(open_database: OpenDatabase, path: Path) -> dict[str, str]:
    database = open_database(path)
    try:
        async with database.write() as session:
            await seed_rich_cosmos(session)
        await simulate(database, EPOCHS)
        return await table_digests(database)
    finally:
        await database.dispose()


async def test_a_seeded_twenty_epoch_run_leaves_an_identical_database(tmp_path: Path, open_database: OpenDatabase) -> None:
    first = await seeded_run(open_database, tmp_path / "first.db")
    second = await seeded_run(open_database, tmp_path / "second.db")
    differing = sorted(name for name in first if first[name] != second.get(name))
    assert differing == []
    whole = hashlib.sha256("".join(first[name] for name in sorted(first)).encode()).hexdigest()
    assert whole == hashlib.sha256("".join(second[name] for name in sorted(second)).encode()).hexdigest()


async def test_one_tick_of_the_reference_world_stays_under_the_tick_target(tmp_path: Path, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "bench.db")
    try:
        async with database.write() as session:
            await seed_rich_cosmos(session)
        target = Rules().engine_budget.tick_target_seconds
        started = time.perf_counter()
        environment = await current_environment(database)
        await run_tick(environment, database)
        await run_epoch_transition(await current_environment(database), database)
        assert time.perf_counter() - started < target
    finally:
        await database.dispose()
