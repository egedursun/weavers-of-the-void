from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.sons import SonDraft, SonRepository
from aerona.db.repositories.worlds import StarDraft, WorldDraft, WorldRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.world import StarType, WorldType
from aerona.domain.models.entity_stats import (
    ArtworkStats,
    EntityStats,
    FactionStats,
    HouseStats,
    ItemStats,
    KnowledgeStats,
    LanguageStats,
    MortalStats,
    PeopleStats,
    PlaceStats,
    PolityStats,
    RegionStats,
    SettlementStats,
    SpeciesStats,
    TraditionStats,
)
from aerona.domain.models.profiles import Personality
from aerona.domain.models.stats import PassionBlock, StatBlock

STATS_BY_TYPE: dict[EntityType, EntityStats] = {
    EntityType.REGION: RegionStats(),
    EntityType.PLACE: PlaceStats(),
    EntityType.SETTLEMENT: SettlementStats(population=500),
    EntityType.PEOPLE: PeopleStats(population=5000),
    EntityType.MORTAL: MortalStats(hp=20, age=30, lifespan=70),
    EntityType.LANGUAGE: LanguageStats(),
    EntityType.SPECIES: SpeciesStats(),
    EntityType.FACTION: FactionStats(),
    EntityType.KNOWLEDGE: KnowledgeStats(level=1),
    EntityType.TRADITION: TraditionStats(),
    EntityType.POLITY: PolityStats(),
    EntityType.HOUSE: HouseStats(),
    EntityType.ITEM: ItemStats(),
    EntityType.ARTWORK: ArtworkStats(),
}


async def seed_world(session: AsyncSession, name: str = "Orvael", star_name: str = "Orvael Sun") -> WorldRow:
    repository = WorldRepository(session)
    star = await repository.create_star(StarDraft(star_name, StarType.YELLOW_DWARF, 70, 0.0, 0.0, 1))
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
            created_epoch=1,
            star_id=star.id,
        )
    )


async def make_entity(
    session: AsyncSession,
    name: str,
    entity_type: EntityType,
    *,
    world_id: int | None = None,
    location_id: int | None = None,
    origin: EntityOrigin = EntityOrigin.ENGINE,
    creator_son_id: int | None = None,
) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=f"The {entity_type.value} called {name}.",
            stats=STATS_BY_TYPE[entity_type],
            power_level=2,
            origin=origin,
            birth_epoch=1,
            world_id=world_id,
            location_id=location_id,
            creator_son_id=creator_son_id,
        )
    )


async def make_son(session: AsyncSession, name: str, world_id: int | None = None) -> SonRow:
    return await SonRepository(session).create(
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
