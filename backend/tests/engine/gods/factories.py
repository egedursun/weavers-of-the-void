from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.sons import SonDraft, SonRepository
from aerona.db.repositories.worlds import StarDraft, WorldDraft, WorldRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EngineKind, EntityOrigin, EntityType, MortalRole
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.world import LoreLanguage, StarType, WorldType
from aerona.domain.models.entity_stats import (
    CultStats,
    EntityStats,
    FactionStats,
    KnowledgeStats,
    LanguageStats,
    MortalStats,
    PeopleStats,
    PlaceStats,
    ProphecyStats,
    RegionStats,
    ResourceStats,
    SettlementStats,
    SpeciesStats,
)
from aerona.domain.models.profiles import Personality
from aerona.domain.models.stats import PassionBlock, StatBlock
from aerona.engine.context import TickContext, TickEnvironment
from aerona.engine.stats import TickStats
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules

SEED = 4242

DEFAULT_STATS: dict[EntityType, EntityStats] = {
    EntityType.REGION: RegionStats(danger=30, fertility=60),
    EntityType.PLACE: PlaceStats(danger=10, fertility=40),
    EntityType.SETTLEMENT: SettlementStats(population=800, prosperity=50, defense=40, piety=50),
    EntityType.PEOPLE: PeopleStats(population=6000, prosperity=50, wealth=40, piety=60, craft=30),
    EntityType.MORTAL: MortalStats(hp=40, strength=40, agility=40, intellect=50, charisma=50, age=30, lifespan=70),
    EntityType.CULT: CultStats(followers=100, zeal=60, influence=40, devotion=0),
    EntityType.FACTION: FactionStats(strength=40, wealth=40, sway=40),
    EntityType.RESOURCE: ResourceStats(abundance=50, value=50, might=30),
    EntityType.SPECIES: SpeciesStats(danger=20),
    EntityType.LANGUAGE: LanguageStats(spread=30),
    EntityType.KNOWLEDGE: KnowledgeStats(level=1),
    EntityType.PROPHECY: ProphecyStats(certainty=50),
}


@dataclass
class GodsWorld:
    cosmos: CosmosRow
    creator: CreatorRow
    world: WorldRow
    region: EntityRow


def published(kind: EventKind, payload: dict[str, Any]) -> None:
    return None


def make_context(session: AsyncSession, rules: Rules, epoch: int, phase: str = "test", seed: int = SEED) -> TickContext:
    environment = TickEnvironment(rules=rules, epoch=epoch, world_seed=seed, lore_language=LoreLanguage.ENGLISH, publish=published, stats=TickStats())
    return TickContext(environment, session, phase)


async def add_world(session: AsyncSession, name: str, epoch: int = 1) -> WorldRow:
    repository = WorldRepository(session)
    star = await repository.create_star(StarDraft(f"{name} Sun", StarType.YELLOW_DWARF, 70, 0.0, 0.0, epoch))
    return await repository.create_world(
        WorldDraft(
            name=name,
            world_type=WorldType.ORDINARY,
            orbit=1.0,
            terrain_seed=f"{name}:seed",
            terrain_sea=0.5,
            terrain_mountains=1.0,
            terrain_humidity=0.0,
            danger=20,
            created_epoch=epoch,
            star_id=star.id,
        )
    )


async def seed_gods_world(session: AsyncSession, epoch: int = 2) -> GodsWorld:
    rules = Rules()
    world = await add_world(session, "Orvael")
    cosmos_repository = CosmosRepository(session)
    cosmos = await cosmos_repository.create(
        CosmosDraft(name="Aerona", rng_seed=SEED, lore_language=LoreLanguage.ENGLISH, seed_idea="test", cosmology="test", tone="test", rules=rules)
    )
    cosmos.epoch = epoch
    creator = await cosmos_repository.create_creator(
        CreatorDraft(name="Aeron", essence=500, mood_contentment=50, mood_anger=20, mood_interest=60, mood_loneliness=30)
    )
    region = await make_entity(session, "Vale of Mist", EntityType.REGION, world_id=world.id)
    await session.flush()
    return GodsWorld(cosmos, creator, world, region)


async def make_entity(
    session: AsyncSession,
    name: str,
    entity_type: EntityType,
    *,
    world_id: int | None = None,
    location_id: int | None = None,
    stats: EntityStats | None = None,
    creator_son_id: int | None = None,
    engine_kind: EngineKind | None = None,
    mortal_role: MortalRole | None = None,
    power_level: int = 2,
    birth_epoch: int = 1,
) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=f"The {entity_type.value} called {name}.",
            stats=stats if stats is not None else DEFAULT_STATS[entity_type],
            power_level=power_level,
            origin=EntityOrigin.ENGINE,
            birth_epoch=birth_epoch,
            world_id=world_id,
            location_id=location_id,
            creator_son_id=creator_son_id,
            engine_kind=engine_kind,
            mortal_role=mortal_role,
            split_title=False,
        )
    )


async def make_son(
    session: AsyncSession, name: str, world_id: int | None = None, *, loyalty: int = 60, wrath: int = 20, essence: int = 100, rarity: Rarity = Rarity.RARE
) -> SonRow:
    return await SonRepository(session).create(
        SonDraft(
            name=name,
            title="the Tester",
            rarity=rarity,
            domains=(Domain.SEA, Domain.SALT),
            stats=StatBlock.uniform(50),
            passions=PassionBlock(loyalty=loyalty, ambition=40, wrath=wrath, mercy=50),
            personality=Personality(temperament="calm"),
            existence=60,
            hp=100,
            essence=essence,
            birth_epoch=1,
            current_world_id=world_id,
        )
    )


async def bond(session: AsyncSession, source: int, target: int, kind: BondKind, epoch: int = 1) -> None:
    await BondRepository(session).connect(BondDraft(source, target, kind, epoch))


async def chronicle_keys(session: AsyncSession) -> list[str]:
    return [key for key in await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)) if key is not None]
