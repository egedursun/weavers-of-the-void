from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select

from aerona.db.session import Database
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.pipeline import EpochRun, simulate
from tests.conftest import OpenDatabase
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 6
SUBSYSTEM_PREFIXES: dict[str, frozenset[str]] = {
    "core": frozenset({"mortal", "monsters", "heroism", "births", "curses", "magic", "spirits", "transition"}),
    "war": frozenset({"war", "diplomacy", "grudges", "faction", "espionage", "tribute", "prisoners"}),
    "society": frozenset({"society", "culture", "religion", "heroes", "disasters", "climate", "works", "wonders", "dialects"}),
    "cosmos": frozenset({"exploration", "travel", "sky", "pantheon", "beyond", "creatures", "cosmos", "horror"}),
    "gods": frozenset({"gods", "sons", "creator", "doom", "essence"}),
}
GROWING = (EntityType.MORTAL, EntityType.SETTLEMENT)


@dataclass(frozen=True)
class Outcome:
    runs: list[EpochRun]
    before: Counter[EntityType]
    after: Counter[EntityType]
    template_keys: Counter[str]
    wars_started: int
    wars_ended: int
    mapped_worlds: int
    founded: Counter[EntityType]


async def census(database: Database) -> Counter[EntityType]:
    async with database.read() as session:
        statement = select(EntityRow.entity_type, func.count()).where(EntityRow.status == EntityStatus.CANON).group_by(EntityRow.entity_type)
        return Counter({entity_type: int(count) for entity_type, count in await session.execute(statement)})


async def seeded_ids(database: Database) -> set[int]:
    async with database.read() as session:
        return set(await session.scalars(select(EntityRow.id)))


async def founded_since(database: Database, seeded: set[int]) -> Counter[EntityType]:
    async with database.read() as session:
        rows = await session.execute(select(EntityRow.id, EntityRow.entity_type))
        return Counter(entity_type for entity_id, entity_type in rows if entity_id not in seeded)


async def run_world(open_database: OpenDatabase, path: Path) -> Outcome:
    database = open_database(path)
    try:
        async with database.write() as session:
            await seed_rich_cosmos(session)
        before = await census(database)
        seeded = await seeded_ids(database)
        runs = await simulate(database, EPOCHS)
        after = await census(database)
        founded = await founded_since(database, seeded)
        async with database.read() as session:
            keys = Counter(key for key in await session.scalars(select(ChronicleRow.template_key)) if key)
            started = int(await session.scalar(select(func.count()).select_from(WarRow)) or 0)
            ended = int(await session.scalar(select(func.count()).select_from(WarRow).where(WarRow.ended_epoch.is_not(None))) or 0)
            mapped = int(await session.scalar(select(func.count()).select_from(WorldMapRow)) or 0)
        return Outcome(runs, before, after, keys, started, ended, mapped, founded)
    finally:
        await database.dispose()


def failures(outcome: Outcome) -> dict[str, int]:
    found: dict[str, int] = {}
    for run in outcome.runs:
        for stats in (run.tick.stats, run.transition):
            found.update({key: value for key, value in stats.counters.items() if key.endswith(".failed")})
    return found


async def test_a_rich_cosmos_lives_six_epochs_deterministically(tmp_path: Path, open_database: OpenDatabase) -> None:
    first = await run_world(open_database, tmp_path / "first.db")
    assert len(first.runs) == EPOCHS
    assert failures(first) == {}
    for entity_type in GROWING:
        assert first.founded[entity_type] > 0, entity_type
    assert first.after[EntityType.MORTAL] > first.before[EntityType.MORTAL]
    assert first.after[EntityType.PEOPLE] >= first.before[EntityType.PEOPLE]
    assert first.wars_started > 0
    assert first.wars_ended > 0
    assert first.mapped_worlds >= 4
    prefixes = {key.split(".", 1)[0] for key in first.template_keys}
    silent = sorted(name for name, expected in SUBSYSTEM_PREFIXES.items() if not expected & prefixes)
    assert silent == []
    second = await run_world(open_database, tmp_path / "second.db")
    assert second.template_keys == first.template_keys
    assert second.after == first.after
    assert (second.wars_started, second.wars_ended) == (first.wars_started, first.wars_ended)
