from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.repositories.sons import SonDraft, SonRepository
from aerona.db.repositories.worlds import StarDraft, WorldDraft, WorldRepository
from aerona.db.session import Database
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import LoreLanguage, StarType, WorldType
from aerona.domain.models.entity_stats import (
    CultStats,
    EntityStats,
    FactionStats,
    ItemStats,
    KnowledgeStats,
    LanguageStats,
    MortalStats,
    OuterBeingStats,
    PeopleStats,
    PlaceStats,
    RegionStats,
    ResourceStats,
    SettlementStats,
    SpeciesStats,
    SpiritStats,
    StructureStats,
    VesselStats,
)
from aerona.domain.models.profiles import Personality
from aerona.domain.models.stats import PassionBlock, StatBlock
from aerona.rules.registry import Rules
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.toolkit import Toolkits, TurnToolkit

SEED = 777
EPOCH = 3

DEFAULT_STATS: dict[EntityType, EntityStats] = {
    EntityType.REGION: RegionStats(danger=30, fertility=60, magic=40),
    EntityType.PLACE: PlaceStats(danger=10, fertility=40),
    EntityType.SETTLEMENT: SettlementStats(population=800, prosperity=50, defense=40, piety=50),
    EntityType.PEOPLE: PeopleStats(population=6000, prosperity=50, wealth=40, piety=60, craft=30, martiality=40),
    EntityType.MORTAL: MortalStats(hp=40, strength=40, agility=40, intellect=50, charisma=50, age=30, lifespan=70),
    EntityType.CULT: CultStats(followers=100, zeal=60, influence=40, devotion=0),
    EntityType.FACTION: FactionStats(strength=40, wealth=40, sway=40),
    EntityType.RESOURCE: ResourceStats(abundance=50, value=50, might=30),
    EntityType.SPECIES: SpeciesStats(hp=40, strength=40, agility=40, intelligence=20, danger=20),
    EntityType.LANGUAGE: LanguageStats(spread=30),
    EntityType.KNOWLEDGE: KnowledgeStats(level=1, spread=10),
    EntityType.ITEM: ItemStats(damage=20, protection=10, might=20, curse=0),
    EntityType.STRUCTURE: StructureStats(splendor=40, durability=40, function=40),
    EntityType.SPIRIT: SpiritStats(strength=30, unrest=30),
    EntityType.VESSEL: VesselStats(speed=40, range=40, crew=10, armor=20, strangeness=10),
    EntityType.OUTER_BEING: OuterBeingStats(size=50, interest=50, influence=60),
}


@dataclass
class Cosmos:
    world_id: int
    region_id: int
    place_id: int
    creator_id: int
    extra: dict[str, int] = field(default_factory=dict)


async def add_world(session: AsyncSession, name: str) -> WorldRow:
    repository = WorldRepository(session)
    star = await repository.create_star(StarDraft(f"{name} Sun", StarType.YELLOW_DWARF, 70, 0.0, 0.0, 1))
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
    world_id: int,
    location_id: int | None = None,
    stats: EntityStats | None = None,
    origin: EntityOrigin = EntityOrigin.ENGINE,
    creator_son_id: int | None = None,
    power: int = 3,
    **extra: Any,
) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=f"The {entity_type.value} called {name}.",
            stats=stats or DEFAULT_STATS.get(entity_type) or DEFAULT_STATS[EntityType.REGION],
            power_level=power,
            origin=origin,
            birth_epoch=1,
            world_id=world_id,
            location_id=location_id,
            creator_son_id=creator_son_id,
            **extra,
        )
    )


async def make_son(
    session: AsyncSession,
    name: str,
    *,
    world_id: int,
    rarity: Rarity = Rarity.RARE,
    essence: int = 120,
    loyalty: int = 60,
    domains: tuple[Domain, Domain] = (Domain.SEA, Domain.SALT),
) -> SonRow:
    return await SonRepository(session).create(
        SonDraft(
            name=name,
            title="the Tester",
            rarity=rarity,
            domains=domains,
            stats=StatBlock.uniform(50),
            passions=PassionBlock(loyalty=loyalty, ambition=40, wrath=20, mercy=50),
            personality=Personality(temperament="calm", appearance="tall"),
            existence=60,
            hp=100,
            essence=essence,
            birth_epoch=1,
            current_world_id=world_id,
        )
    )


async def connect(session: AsyncSession, source: int, target: int, kind: BondKind, description: str | None = None) -> None:
    await BondRepository(session).connect(BondDraft(source, target, kind, 1, description))


async def seed_cosmos(session: AsyncSession) -> Cosmos:
    world = await add_world(session, "Orvael")
    repository = CosmosRepository(session)
    cosmos = await repository.create(
        CosmosDraft(name="Aerona", rng_seed=SEED, lore_language=LoreLanguage.ENGLISH, seed_idea="test", cosmology="test", tone="test", rules=Rules())
    )
    cosmos.epoch = EPOCH
    cosmos.primary_world_id = world.id
    creator = await repository.create_creator(CreatorDraft(name="Aeron", essence=500, mood_contentment=50, mood_anger=20, mood_interest=60, mood_loneliness=30))
    region = await make_entity(session, "Vale of Mist", EntityType.REGION, world_id=world.id)
    place = await make_entity(session, "Ember Hollow", EntityType.PLACE, world_id=world.id, location_id=region.id)
    await session.flush()
    return Cosmos(world.id, region.id, place.id, creator.id)


async def son_toolkit(database: Database, son_id: int, action_points: int = 3, ports: ToolPorts | None = None, rules: Rules | None = None) -> TurnToolkit:
    return await Toolkits(database, ports, rules=rules).son_toolkit(son_id, EPOCH, action_points)


async def mortal_toolkit(database: Database, entity_id: int, action_points: int = 3, ports: ToolPorts | None = None, rules: Rules | None = None) -> TurnToolkit:
    return await Toolkits(database, ports, rules=rules).mortal_toolkit(entity_id, EPOCH, action_points)


async def count_rows(database: Database, table: Any) -> int:
    async with database.read() as session:
        return int(await session.scalar(select(func.count()).select_from(table)) or 0)


DESCRIPTION = (
    "A hollow of black salt where the tide never quite leaves, glittering at dusk with brine that hums when touched; "
    "fishers say it was cut by a falling star and only children can hear its song."
)


@dataclass
class Realm:
    cosmos: Cosmos
    son_id: int
    sibling_id: int
    people_id: int
    settlement_id: int
    mortal_id: int
    resource_id: int
    species_id: int
    language_id: int
    knowledge_id: int
    cult_id: int
    faction_id: int
    other_world_id: int
    other_people_id: int
    route_id: int
    god_id: int


async def seed_realm(database: Database, rarity: Rarity = Rarity.MYTHIC) -> Realm:
    async with database.write() as session:
        cosmos = await seed_cosmos(session)
        world, region = cosmos.world_id, cosmos.region_id
        son = await make_son(session, "Thalor", world_id=world, rarity=rarity, essence=400, loyalty=20)
        sibling = await make_son(session, "Veyra", world_id=world, rarity=Rarity.RARE, essence=120, domains=(Domain.FIRE, Domain.ASH))
        people = await make_entity(session, "Kessar Folk", EntityType.PEOPLE, world_id=world, location_id=region)
        settlement = await make_entity(session, "Brinewatch", EntityType.SETTLEMENT, world_id=world, location_id=region)
        mortal = await make_entity(session, "Ilsa Morrow", EntityType.MORTAL, world_id=world, location_id=settlement.id)
        resource = await make_entity(
            session, "Saltglass Vein", EntityType.RESOURCE, world_id=world, location_id=region, creator_son_id=son.id, origin=EntityOrigin.SON
        )
        species = await make_entity(session, "Duskhound", EntityType.SPECIES, world_id=world, location_id=region)
        language = await make_entity(session, "Kessari", EntityType.LANGUAGE, world_id=world)
        knowledge = await make_entity(session, "Tidecraft", EntityType.KNOWLEDGE, world_id=world, knowledge_branch=KnowledgeBranch.SEAFARING)
        cult = await make_entity(session, "Order of Brine", EntityType.CULT, world_id=world, location_id=region)
        faction = await make_entity(session, "Red Oars", EntityType.FACTION, world_id=world, location_id=region)
        other = await add_world(session, "Velmor")
        other_region = await make_entity(session, "Far Dunes", EntityType.REGION, world_id=other.id)
        other_people = await make_entity(session, "Dune Kin", EntityType.PEOPLE, world_id=other.id, location_id=other_region.id)
        route = RouteRow(world_a_id=world, world_b_id=other.id, method=TravelMethod.LIGHT_SAIL, duration_epochs=2, danger=20, created_epoch=1)
        session.add(route)
        god = await ForeignGodRepository(session).create(ForeignGodDraft("Ombrun", world, Domain.STORM, 40, StatBlock.uniform(40), 1, title="the Old"))
        god.contacted = True
        await connect(session, people.id, language.id, BondKind.SPEAKS)
        await connect(session, people.id, son.id, BondKind.WORSHIPS)
        await connect(session, cult.id, son.id, BondKind.WORSHIPS)
        await connect(session, mortal.id, knowledge.id, BondKind.KNOWS)
        await BondRepository(session).connect(BondDraft(people.id, settlement.id, BondKind.RULES, 1, role=BondRole.HOMELAND))
        await session.flush()
        return Realm(
            cosmos,
            son.id,
            sibling.id,
            people.id,
            settlement.id,
            mortal.id,
            resource.id,
            species.id,
            language.id,
            knowledge.id,
            cult.id,
            faction.id,
            other.id,
            other_people.id,
            route.id,
            god.id,
        )
