import argparse
import asyncio
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from aerona.db import tables
from aerona.db.base import Base
from aerona.db.migrations import build_config
from aerona.db.session import Database
from aerona.db.tables.body import ConditionRow, InjuryRow
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.childhood import PedagogyRow
from aerona.db.tables.city_rules import ConurbationRow
from aerona.db.tables.commerce import ShopRow
from aerona.db.tables.competition import CartelRow, MarketStructureRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.tables.death_work import DeathWorkRow
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.disease_agents import DiseaseAgentRow
from aerona.db.tables.divine_conceptions import DivineConceptionRow
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.db.tables.fertility_means import FertilityMeansRow
from aerona.db.tables.folk_knowledge import FolkClassRow
from aerona.db.tables.forecasting import WeatherWorkRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.tables.honours import HonourHeldRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.interpretation import InterpretationRow
from aerona.db.tables.interworld import InterworldCampaignRow
from aerona.db.tables.intimacy import RestraintCustomRow
from aerona.db.tables.kin import KinGroupRow
from aerona.db.tables.kin_dynamics import KinDynamicRow
from aerona.db.tables.labour import LabourDisputeRow
from aerona.db.tables.leader_cults import LeaderCultRow
from aerona.db.tables.leagues import PolityLeagueRow
from aerona.db.tables.mass_weapons import MassWeaponRow
from aerona.db.tables.media import MediaOutletRow
from aerona.db.tables.monetary import MonetaryAuthorityRow
from aerona.db.tables.occupation_regimes import OccupationRegimeRow
from aerona.db.tables.orders import EconomicOrderRow
from aerona.db.tables.plants import PlantAnatomyRow, PlantPartRow
from aerona.db.tables.population import PopulationPolicyRow
from aerona.db.tables.protected_nature import ProtectedAreaRow
from aerona.db.tables.reckoning import ReckoningRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.db.tables.restoration import RestorationRow
from aerona.db.tables.rule_override import RuleOverrideRow
from aerona.db.tables.sea_waves import SeaWaveRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.space_weather import WorldFieldRow
from aerona.db.tables.speech import SpeechRow
from aerona.db.tables.standing import ProfessionOfValueRow
from aerona.db.tables.warfare import WarRow
from aerona.db.tables.water import CoastRow
from aerona.db.tables.works import PublicWorksRow
from aerona.db.tables.youth import YouthGroupMemberRow, YouthGroupRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.interpretation import InterpretationFault
from aerona.domain.enums.works import WorksStatus
from aerona.engine.body.marks import marked
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


async def order_measures(session: AsyncSession, epochs: int) -> dict[str, float]:
    polities, towns = (
        await living(session, EntityType.POLITY),
        await living(session, EntityType.SETTLEMENT),
    )
    peoples, regions = (
        await living(session, EntityType.PEOPLE),
        await living(session, EntityType.REGION),
    )
    mortals, factions = (
        await living(session, EntityType.MORTAL),
        await living(session, EntityType.FACTION),
    )
    faiths, houses = (
        await living(session, EntityType.CULT),
        await living(session, EntityType.HOUSE),
    )
    per_epoch = max(1, epochs)
    return {
        "economic_orders_per_polity": await count(session, EconomicOrderRow)
        / max(1, polities),
        "governed_share_of_factions_pct": share(
            await count(
                session,
                OrgGovernanceRow,
                OrgGovernanceRow.org_node_id.in_(
                    select(EntityRow.id).where(
                        EntityRow.entity_type == EntityType.FACTION,
                        EntityRow.status == EntityStatus.CANON,
                    )
                ),
            ),
            factions,
        ),
        "cartels_per_market": await count(session, CartelRow)
        / max(1, await count(session, MarketStructureRow)),
        "labour_disputes_per_epoch": await count(session, LabourDisputeRow) / per_epoch,
        "monetary_authorities_per_polity": await count(session, MonetaryAuthorityRow)
        / max(1, polities),
        "holdings_per_security": await count(session, SecurityHoldingRow)
        / max(1, await count(session, IssuedSecurityRow)),
        "leagues_per_polity": await count(session, PolityLeagueRow) / max(1, polities),
        "conurbations_per_town": await count(session, ConurbationRow) / max(1, towns),
        "protected_regions_share_pct": share(
            await count(
                session, ProtectedAreaRow, ProtectedAreaRow.lifted_epoch.is_(None)
            ),
            regions,
        ),
        "departures_per_epoch": await count(session, DepartureRow) / per_epoch,
        "referendums_per_epoch": await count(session, ReferendumRow) / per_epoch,
        "reckonings_per_epoch": await count(session, ReckoningRow) / per_epoch,
        "leader_cults_per_polity": await count(session, LeaderCultRow)
        / max(1, polities),
        "restorations_per_epoch": await count(session, RestorationRow) / per_epoch,
        "occupation_regimes_per_epoch": await count(session, OccupationRegimeRow)
        / per_epoch,
        "mass_weapons_per_polity": await count(session, MassWeaponRow)
        / max(1, polities),
        "interworld_campaigns_per_epoch": await count(session, InterworldCampaignRow)
        / per_epoch,
        "kin_dynamics_per_house": await count(session, KinDynamicRow) / max(1, houses),
        "moods_per_town": await count(
            session,
            FeelingSpreadRow,
            FeelingSpreadRow.settlement_entity_id.is_not(None),
        )
        / max(1, towns),
        "faulty_interpretations_share_pct": share(
            await count(
                session,
                InterpretationRow,
                InterpretationRow.fault != InterpretationFault.NONE,
            ),
            await count(session, InterpretationRow),
        ),
        "robbed_graves_share_pct": share(
            await count(
                session, GraveGoodsRow, GraveGoodsRow.robbed_epoch.is_not(None)
            ),
            await count(session, GraveGoodsRow),
        ),
        "agentless_conditions_per_hundred_mortals": 100
        * await count(session, ConditionRow, ConditionRow.kind_id.is_not(None))
        / max(1, mortals),
        "fertility_means_per_people": await count(session, FertilityMeansRow)
        / max(1, peoples),
        "honours_held_per_hundred_mortals": 100
        * await count(session, HonourHeldRow, HonourHeldRow.revoked_epoch.is_(None))
        / max(1, mortals),
        "sea_waves_per_epoch": await count(session, SeaWaveRow) / per_epoch,
        "creature_groups_per_region": await count(session, CreatureGroupRow)
        / max(1, regions),
        "conceptions_per_faith": await count(
            session,
            DivineConceptionRow,
            DivineConceptionRow.cult_entity_id.in_(
                select(EntityRow.id).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON)
            ),
        )
        / max(1, faiths),
    }


async def community_count(database: Database) -> int:
    async with database.read() as session:
        return int(
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


async def measure(
    database: Database,
    epochs: int,
    start_doom: int,
    settled_communities: int,
    settled_epochs: int,
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
            await session.scalars(select(InjuryRow.bearer_node_id).where(marked()))
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
        families = await family_measures(session, epochs) | await order_measures(
            session, epochs
        )
    return families | {
        "wars_per_epoch": wars / max(1, epochs),
        "mean_age_at_death": sum(base_stat(row, "age") or 0 for row in dead) / len(dead)
        if dead
        else 0.0,
        "maimed_share_pct": 100
        * sum(1 for row in living if row.id in maimed)
        / max(1, len(living)),
        "community_growth_per_epoch_pct": 100
        * (communities - settled_communities)
        / max(1, settled_communities)
        / max(1, settled_epochs),
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
            settled = epochs // 2
            await simulate(database, settled)
            settled_communities = await community_count(database)
            await simulate(database, epochs - settled)
            return await measure(
                database, epochs, start_doom, settled_communities, epochs - settled
            )
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
