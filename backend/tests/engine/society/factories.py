from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.model import ElevationClass, RegionRecord
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.sons import SonDraft, SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldMapRow, WorldRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import TradeMode, TradeRouteStatus
from aerona.domain.enums.entity import EntityOrigin, EntityType, MortalRole
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.entity_stats import (
    EntityStats,
    KnowledgeStats,
    MortalStats,
    NaturalLawStats,
    PeopleStats,
    RegionStats,
    SettlementStats,
    TradeRouteStats,
)
from aerona.domain.models.profiles import Personality
from aerona.domain.models.stats import PassionBlock, StatBlock
from aerona.engine.context import TickContext, TickEnvironment
from aerona.engine.stats import TickStats
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from tests.db.factories import seed_world

WORLD_SEED = 11


@dataclass(frozen=True)
class Realm:
    session: AsyncSession
    world: WorldRow
    region: EntityRow
    far_region: EntityRow


def tuned(base: Rules | None = None, **namespaces: dict[str, Any]) -> Rules:
    rules = base or Rules()
    changes = {name: replace(getattr(rules, name), **values) for name, values in namespaces.items()}
    return replace(rules, **changes)


def _silent(_kind: EventKind, _payload: dict[str, Any]) -> None:
    return None


def context(session: AsyncSession, rules: Rules | None = None, epoch: int = 3, phase: str = "test") -> TickContext:
    environment = TickEnvironment(
        rules=rules or Rules(), epoch=epoch, world_seed=WORLD_SEED, lore_language=LoreLanguage.ENGLISH, publish=_silent, stats=TickStats()
    )
    return TickContext(environment, session, phase)


def region_record(region_id: int, *, neighbours: list[int], coastal: bool = False, elevation: ElevationClass = ElevationClass.PLAIN) -> dict[str, Any]:
    record = RegionRecord(
        id=region_id,
        parent_id=None,
        top_level_id=region_id,
        depth=0,
        is_water=False,
        seed=None,
        anchor=None,
        centroid=None,
        size=10,
        coastal=coastal,
        mean_elevation=0.5,
        elevation_class=elevation,
        climate=[],
        neighbours=neighbours,
        bordering=neighbours,
    )
    return record.model_dump(mode="json")


async def store_map(session: AsyncSession, world_id: int, records: list[dict[str, Any]]) -> None:
    existing = await session.get(WorldMapRow, world_id)
    if existing is None:
        session.add(WorldMapRow(world_id=world_id, generator_version=1, epoch=1, geometry={"regions": records}))
    else:
        existing.geometry = {"regions": records}
    await session.flush()


async def make(
    session: AsyncSession,
    name: str,
    entity_type: EntityType,
    stats: EntityStats,
    *,
    world_id: int,
    location_id: int | None = None,
    birth_epoch: int = 1,
    **extra: Any,
) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=f"The {entity_type.value} {name}.",
            stats=stats,
            power_level=extra.pop("power_level", 2),
            origin=EntityOrigin.ENGINE,
            birth_epoch=birth_epoch,
            world_id=world_id,
            location_id=location_id,
            split_title=False,
            **extra,
        )
    )


async def build_realm(session: AsyncSession) -> Realm:
    world = await seed_world(session)
    region = await make(session, "Vale", EntityType.REGION, RegionStats(fertility=60), world_id=world.id)
    far = await make(session, "Waste", EntityType.REGION, RegionStats(fertility=20), world_id=world.id)
    await store_map(session, world.id, [region_record(region.id, neighbours=[]), region_record(far.id, neighbours=[])])
    return Realm(session, world, region, far)


async def settlement(realm: Realm, name: str, *, population: int = 3000, prosperity: int = 50, location_id: int | None = None) -> EntityRow:
    stats = SettlementStats(population=population, prosperity=prosperity, defense=40, piety=50)
    return await make(realm.session, name, EntityType.SETTLEMENT, stats, world_id=realm.world.id, location_id=location_id or realm.region.id)


async def people(realm: Realm, name: str, *, population: int = 5000, location_id: int | None = None, **values: int) -> EntityRow:
    stats = PeopleStats(population=population, prosperity=values.get("prosperity", 50), piety=values.get("piety", 50), wealth=values.get("wealth", 40))
    return await make(realm.session, name, EntityType.PEOPLE, stats, world_id=realm.world.id, location_id=location_id or realm.region.id)


async def mortal(realm: Realm, name: str, *, location_id: int | None = None, role: MortalRole | None = None, **values: int) -> EntityRow:
    stats = MortalStats(
        hp=values.get("hp", 100),
        strength=values.get("strength", 50),
        agility=values.get("agility", 50),
        intellect=values.get("intellect", 50),
        charisma=values.get("charisma", 50),
        age=values.get("age", 30),
        lifespan=values.get("lifespan", 70),
    )
    return await make(realm.session, name, EntityType.MORTAL, stats, world_id=realm.world.id, location_id=location_id or realm.region.id, mortal_role=role)


async def knowledge(realm: Realm, name: str, branch: KnowledgeBranch, spread: int = 20) -> EntityRow:
    stats = KnowledgeStats(level=1, spread=spread)
    return await make(realm.session, name, EntityType.KNOWLEDGE, stats, world_id=realm.world.id, knowledge_branch=branch)


async def natural_law(realm: Realm, name: str, law: NaturalLaw) -> EntityRow:
    return await make(realm.session, name, EntityType.NATURAL_LAW, NaturalLawStats(), world_id=realm.world.id, natural_law=law)


async def son(session: AsyncSession, name: str, world_id: int | None, charisma: int = 50, fame: int = 0) -> SonRow:
    created = await SonRepository(session).create(
        SonDraft(
            name=name,
            title="the Tester",
            rarity=Rarity.RARE,
            domains=(Domain.SEA, Domain.SALT),
            stats=StatBlock.uniform(50),
            passions=PassionBlock(loyalty=60, ambition=40, wrath=20, mercy=50),
            personality=Personality(temperament="calm"),
            existence=60,
            hp=100,
            essence=50,
            birth_epoch=1,
            current_world_id=world_id,
        )
    )
    created.charisma = charisma
    created.fame = fame
    await session.flush()
    return created


async def link(session: AsyncSession, source: int, target: int, kind: BondKind, *, epoch: int = 1, description: str | None = None) -> BondRow:
    return await BondRepository(session).connect(BondDraft(source, target, kind, epoch, description))


async def active_bonds(session: AsyncSession, source: int, kind: BondKind) -> list[BondRow]:
    statement = select(BondRow).where(BondRow.source_node_id == source, BondRow.kind == kind, BondRow.state == BondState.ACTIVE)
    return list(await session.scalars(statement.order_by(BondRow.id)))


async def bonded(session: AsyncSession, first: int, second: int, kind: BondKind) -> bool:
    return await BondRepository(session).exists_between(first, second, kind)


async def chronicle_keys(session: AsyncSession) -> list[str]:
    return [key for key in await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)) if key is not None]


async def named(session: AsyncSession, entity_type: EntityType) -> list[EntityRow]:
    return list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == entity_type).order_by(EntityRow.id)))


async def trade_route(realm: Realm, first: EntityRow, second: EntityRow) -> EntityRow:
    stats = TradeRouteStats(capacity=40, danger=0, renown=0, culture=0)
    road = await make(realm.session, f"Road of {first.name}", EntityType.TRADE_ROUTE, stats, world_id=realm.world.id, location_id=realm.region.id)
    realm.session.add(
        TradeRouteProfileRow(
            route_entity_id=road.id,
            first_market_id=first.id,
            second_market_id=second.id,
            mode=TradeMode.ROAD,
            status=TradeRouteStatus.OPEN,
            length=1,
            founded_epoch=1,
        )
    )
    await realm.session.flush()
    return road
