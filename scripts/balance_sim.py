import argparse
import asyncio
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from sqlalchemy import func, select

from aerona.db import tables
from aerona.db.base import Base
from aerona.db.migrations import build_config
from aerona.db.session import Database
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.body import LASTING_INJURY_STATES
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.engine.pipeline import simulate
from aerona.engine.primitives.stats import base_stat
from tests.engine.integration.factories import seed_rich_cosmos

assert tables

ROOT = Path(__file__).resolve().parent.parent
BANDS = ROOT / "docs" / "spec" / "13-balance-bands.json"
HOSTILE_BELOW = -60


@dataclass(frozen=True)
class Band:
    metric: str
    low: float
    high: float
    meaning: str


def load_bands() -> list[Band]:
    data = json.loads(BANDS.read_text(encoding="utf-8"))
    return [Band(item["metric"], item["low"], item["high"], item["meaning"]) for item in data["bands"]]


async def measure(database: Database, epochs: int, start_doom: int, start_communities: int) -> dict[str, float]:
    async with database.read() as session:
        wars = int(await session.scalar(select(func.count()).select_from(WarRow)) or 0)
        mortals = list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL)))
        dead = [row for row in mortals if row.status is EntityStatus.DEAD and base_stat(row, "age") is not None]
        living = [row for row in mortals if row.status is EntityStatus.CANON]
        maimed = set(await session.scalars(select(InjuryRow.bearer_node_id).where(InjuryRow.state.in_(list(LASTING_INJURY_STATES)))))
        communities = int(
            await session.scalar(
                select(func.count()).select_from(EntityRow).where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON)
            )
            or 0
        )
        relations = list(await session.scalars(select(CommunityRelationRow.value)))
        cosmos = await session.get(CosmosRow, 1)
    return {
        "wars_per_epoch": wars / max(1, epochs),
        "mean_age_at_death": sum(base_stat(row, "age") or 0 for row in dead) / len(dead) if dead else 0.0,
        "maimed_share_pct": 100 * sum(1 for row in living if row.id in maimed) / max(1, len(living)),
        "community_growth_per_epoch_pct": 100 * (communities - start_communities) / max(1, start_communities) / max(1, epochs),
        "hostile_pair_share_pct": 100 * sum(1 for value in relations if value <= HOSTILE_BELOW) / max(1, len(relations)),
        "doom_per_epoch": ((cosmos.doom_clock if cosmos is not None else 0) - start_doom) / max(1, epochs),
    }


async def run(epochs: int) -> dict[str, float]:
    with tempfile.TemporaryDirectory() as folder:
        url = f"sqlite+aiosqlite:///{folder}/balance.db"
        database = Database(url)
        try:
            async with database.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            await asyncio.to_thread(command.stamp, build_config(url), "head")
            async with database.write() as session:
                await seed_rich_cosmos(session)
                cosmos = await session.get(CosmosRow, 1)
                start_doom = cosmos.doom_clock if cosmos is not None else 0
                start_communities = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(EntityRow)
                        .where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON)
                    )
                    or 0
                )
            await simulate(database, epochs)
            return await measure(database, epochs, start_doom, start_communities)
        finally:
            await database.dispose()


def outside(values: dict[str, float]) -> list[str]:
    return [
        f"{band.metric} = {values[band.metric]:.2f} outside [{band.low}, {band.high}]"
        for band in load_bands()
        if not band.low <= values[band.metric] <= band.high
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=100)
    epochs = parser.parse_args().epochs
    values = asyncio.run(run(epochs))
    for key, value in values.items():
        print(f"{key}: {value:.2f}")
    problems = outside(values)
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
