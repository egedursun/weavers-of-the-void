import argparse
import asyncio
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from aerona.db import tables
from aerona.db.base import Base
from aerona.db.migrations import build_config
from aerona.db.session import Database
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.childhood import PedagogyRow
from aerona.db.tables.commerce import ShopRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.death_work import DeathWorkRow
from aerona.db.tables.disease_agents import DiseaseAgentRow
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folk_knowledge import FolkClassRow
from aerona.db.tables.forecasting import WeatherWorkRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.intimacy import RestraintCustomRow
from aerona.db.tables.kin import KinGroupRow
from aerona.db.tables.media import MediaOutletRow
from aerona.db.tables.plants import PlantAnatomyRow, PlantPartRow
from aerona.db.tables.population import PopulationPolicyRow
from aerona.db.tables.rule_override import RuleOverrideRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.space_weather import WorldFieldRow
from aerona.db.tables.speech import SpeechRow
from aerona.db.tables.standing import ProfessionOfValueRow
from aerona.db.tables.warfare import WarRow
from aerona.db.tables.water import CoastRow
from aerona.db.tables.works import PublicWorksRow
from aerona.db.tables.youth import YouthGroupMemberRow, YouthGroupRow
from aerona.domain.enums.body import LASTING_INJURY_STATES
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.works import WorksStatus
from aerona.engine.pipeline import simulate
from aerona.engine.primitives.stats import base_stat
from alembic import command
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
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
    return [
        Band(item["metric"], item["low"], item["high"], item["meaning"])
        for item in data["bands"]
    ]


async def count(
    session: AsyncSession, model: type[Base], *where: ColumnElement[bool]
) -> int:
    return int(
        await session.scalar(select(func.count()).select_from(model).where(*where)) or 0
    )


async def mean(
    session: AsyncSession, column: InstrumentedAttribute[int], otherwise: float = 0.0
) -> float:
    found = await session.scalar(select(func.avg(column)))
    return float(found) if found is not None else otherwise


async def living(session: AsyncSession, kind: EntityType) -> int:
    return await count(
        session,
        EntityRow,
        EntityRow.entity_type == kind,
        EntityRow.status == EntityStatus.CANON,
    )


def share(part: int, whole: int) -> float:
    return 100 * part / max(1, whole)


async def family_measures(session: AsyncSession, epochs: int) -> dict[str, float]:
    peoples, towns = (
        await living(session, EntityType.PEOPLE),
        await living(session, EntityType.SETTLEMENT),
    )
    regions, polities = (
        await living(session, EntityType.REGION),
        await living(session, EntityType.POLITY),
    )
    groups = await count(session, YouthGroupRow)
    plants = await count(session, PlantAnatomyRow)
    return {
        "population_policies_per_polity": await count(session, PopulationPolicyRow)
        / max(1, polities),
        "outlet_mean_trust": await mean(session, MediaOutletRow.trust, 50.0),
        "shops_per_town": await count(session, ShopRow) / max(1, towns),
        "failed_works_share_pct": share(
            await count(
                session, PublicWorksRow, PublicWorksRow.status == WorksStatus.FAILED
            ),
            await count(session, PublicWorksRow),
        ),
        "household_mean_servants": await mean(session, HouseholdRow.servants),
        "kin_groups_per_people": await count(session, KinGroupRow) / max(1, peoples),
        "folk_misclassified_share_pct": share(
            await count(session, FolkClassRow, FolkClassRow.misclassified.is_(True)),
            await count(session, FolkClassRow),
        ),
        "restraint_customs_per_people": await count(session, RestraintCustomRow)
        / max(1, peoples),
        "pedagogies_per_people": await count(session, PedagogyRow) / max(1, peoples),
        "endowments_per_town": await count(session, EndowmentRow) / max(1, towns),
        "youth_group_mean_size": await count(session, YouthGroupMemberRow)
        / max(1, groups),
        "death_work_roles_per_people": await count(session, DeathWorkRow)
        / max(1, peoples),
        "speeches_per_epoch": await count(session, SpeechRow) / max(1, epochs),
        "world_mean_surface_dose": await mean(session, WorldFieldRow.surface_dose),
        "coast_mean_silting": await mean(session, CoastRow.harbour_silting),
        "disease_mean_cure_overuse": await mean(session, DiseaseAgentRow.overuse),
        "body_system_failed_share_pct": share(
            await count(session, BodySystemRow, BodySystemRow.failed.is_(True)),
            await count(session, BodySystemRow),
        ),
        "plant_parts_per_plant": await count(session, PlantPartRow) / max(1, plants),
        "fossil_beds_per_region": await count(session, FossilBedRow) / max(1, regions),
        "weather_works_per_region": await count(session, WeatherWorkRow)
        / max(1, regions),
        "professions_exposed_share_pct": share(
            await count(
                session, ProfessionOfValueRow, ProfessionOfValueRow.exposed.is_(True)
            ),
            await count(session, ProfessionOfValueRow),
        ),
    }


async def measure(
    database: Database, epochs: int, start_doom: int, start_communities: int
) -> dict[str, float]:
    async with database.read() as session:
        wars = int(await session.scalar(select(func.count()).select_from(WarRow)) or 0)
        mortals = list(
            await session.scalars(
                select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL)
            )
        )
        dead = [
            row
            for row in mortals
            if row.status is EntityStatus.DEAD and base_stat(row, "age") is not None
        ]
        living = [row for row in mortals if row.status is EntityStatus.CANON]
        maimed = set(
            await session.scalars(
                select(InjuryRow.bearer_node_id).where(
                    InjuryRow.state.in_(list(LASTING_INJURY_STATES))
                )
            )
        )
        communities = int(
            await session.scalar(
                select(func.count())
                .select_from(EntityRow)
                .where(
                    EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
                    EntityRow.status == EntityStatus.CANON,
                )
            )
            or 0
        )
        relations = list(await session.scalars(select(CommunityRelationRow.value)))
        cosmos = await session.get(CosmosRow, 1)
        families = await family_measures(session, epochs)
    return families | {
        "wars_per_epoch": wars / max(1, epochs),
        "mean_age_at_death": sum(base_stat(row, "age") or 0 for row in dead) / len(dead)
        if dead
        else 0.0,
        "maimed_share_pct": 100
        * sum(1 for row in living if row.id in maimed)
        / max(1, len(living)),
        "community_growth_per_epoch_pct": 100
        * (communities - start_communities)
        / max(1, start_communities)
        / max(1, epochs),
        "hostile_pair_share_pct": 100
        * sum(1 for value in relations if value <= HOSTILE_BELOW)
        / max(1, len(relations)),
        "doom_per_epoch": (
            (cosmos.doom_clock if cosmos is not None else 0) - start_doom
        )
        / max(1, epochs),
    }


async def run(
    epochs: int, overrides: dict[str, float] | None = None
) -> dict[str, float]:
    with tempfile.TemporaryDirectory() as folder:
        url = f"sqlite+aiosqlite:///{folder}/balance.db"
        database = Database(url)
        try:
            async with database.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            await asyncio.to_thread(command.stamp, build_config(url), "head")
            async with database.write() as session:
                await seed_rich_cosmos(session)
                for name, value in sorted((overrides or {}).items()):
                    namespace, key = name.split(".", 1)
                    session.add(
                        RuleOverrideRow(namespace=namespace, key=key, value=value)
                    )
                cosmos = await session.get(CosmosRow, 1)
                start_doom = cosmos.doom_clock if cosmos is not None else 0
                start_communities = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(EntityRow)
                        .where(
                            EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
                            EntityRow.status == EntityStatus.CANON,
                        )
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
