from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.sons import SonDraft, SonRepository
from aerona.db.repositories.worlds import StarDraft, WorldDraft, WorldRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityOrigin, EntityType, MortalRole
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.world import LoreLanguage, StarType, WorldType
from aerona.domain.models.entity_stats import (
    EntityStats,
    EventStats,
    KnowledgeStats,
    LanguageStats,
    LegendStats,
    MortalStats,
    PeopleStats,
    PlaceStats,
    ProphecyStats,
    RegionStats,
    SettlementStats,
    SpeciesStats,
    TraditionStats,
)
from aerona.domain.models.profiles import Personality
from aerona.domain.models.stats import PassionBlock, StatBlock
from aerona.rules.registry import Rules

SEED = 4242

DEFAULT_STATS: dict[EntityType, EntityStats] = {
    EntityType.REGION: RegionStats(breadth=50, fertility=60, magic=30, danger=20),
    EntityType.PLACE: PlaceStats(danger=10),
    EntityType.SETTLEMENT: SettlementStats(population=800),
    EntityType.PEOPLE: PeopleStats(population=4000),
    EntityType.MORTAL: MortalStats(hp=30, age=30, lifespan=70),
    EntityType.LANGUAGE: LanguageStats(spread=30),
    EntityType.SPECIES: SpeciesStats(danger=20),
    EntityType.KNOWLEDGE: KnowledgeStats(level=1),
    EntityType.TRADITION: TraditionStats(),
    EntityType.LEGEND: LegendStats(),
    EntityType.EVENT: EventStats(),
    EntityType.PROPHECY: ProphecyStats(),
}


@dataclass
class Cosmos:
    cosmos: CosmosRow
    creator: CreatorRow
    world: WorldRow
    son: SonRow
    region: EntityRow
    people: EntityRow
    extra: dict[str, EntityRow] = field(default_factory=dict)


def son_draft(name: str, world_id: int | None, rarity: Rarity = Rarity.RARE) -> SonDraft:
    return SonDraft(
        name=name,
        title="the Watcher",
        rarity=rarity,
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


async def make_entity(
    session: AsyncSession,
    name: str,
    entity_type: EntityType,
    *,
    world_id: int,
    location_id: int | None = None,
    origin: EntityOrigin = EntityOrigin.ENGINE,
    creator_son_id: int | None = None,
    birth_epoch: int = 1,
    power_level: int = 2,
    description: str | None = None,
    mortal_role: MortalRole | None = None,
    stats: EntityStats | None = None,
) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=description or f"The {entity_type.value} called {name}.",
            stats=stats or DEFAULT_STATS[entity_type],
            power_level=power_level,
            origin=origin,
            birth_epoch=birth_epoch,
            world_id=world_id,
            location_id=location_id,
            creator_son_id=creator_son_id,
            mortal_role=mortal_role,
            split_title=False,
        )
    )


async def make_son(session: AsyncSession, name: str, world_id: int | None, rarity: Rarity = Rarity.RARE) -> SonRow:
    return await SonRepository(session).create(son_draft(name, world_id, rarity))


async def make_world(session: AsyncSession, name: str, created_epoch: int = 1) -> WorldRow:
    worlds = WorldRepository(session)
    star = await worlds.create_star(StarDraft(f"{name} Star", StarType.YELLOW_DWARF, 70, 1.0, 1.0, created_epoch))
    return await worlds.create_world(
        WorldDraft(
            name=name,
            world_type=WorldType.ORDINARY,
            orbit=1.0,
            terrain_seed=name,
            terrain_sea=0.4,
            terrain_mountains=1.0,
            terrain_humidity=0.0,
            danger=20,
            created_epoch=created_epoch,
            star_id=star.id,
        )
    )


async def bond(session: AsyncSession, source: int, target: int, kind: BondKind, *, epoch: int = 1, description: str | None = None) -> None:
    await BondRepository(session).connect(BondDraft(source, target, kind, epoch, description=description))


async def seed_cosmos(session: AsyncSession, rules: Rules | None = None, epoch: int = 1) -> Cosmos:
    cosmos = await CosmosRepository(session).create(
        CosmosDraft(
            name="Aerona",
            rng_seed=SEED,
            lore_language=LoreLanguage.ENGLISH,
            seed_idea="A world of salt and tides.",
            cosmology="Seas hold the sky.",
            tone="quiet",
            rules=rules or Rules(),
        )
    )
    cosmos.epoch = epoch
    creator = await CosmosRepository(session).create_creator(
        CreatorDraft(name="Aeron", essence=150, mood_contentment=50, mood_anger=10, mood_interest=50, mood_loneliness=20)
    )
    world = await make_world(session, "Velar")
    cosmos.primary_world_id = world.id
    son = await make_son(session, "Ithren", world.id)
    region = await make_entity(session, "Amberreach", EntityType.REGION, world_id=world.id)
    people = await make_entity(session, "Velari Folk", EntityType.PEOPLE, world_id=world.id, location_id=region.id)
    await session.flush()
    return Cosmos(cosmos=cosmos, creator=creator, world=world, son=son, region=region, people=people)
