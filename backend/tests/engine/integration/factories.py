from dataclasses import dataclass, field, replace

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.sons import SonRepository
from aerona.db.repositories.worlds import WorldDraft, WorldRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import (
    CelestialStats,
    CultStats,
    LanguageStats,
    MortalStats,
    PeopleStats,
    RegionStats,
    ResourceStats,
    SettlementStats,
    SpeciesStats,
)
from tests.engine.core.factories import CoreWorld, bond, entity, knowledge, seed_rich_world, son_draft


@dataclass
class Frontier:
    world: WorldRow
    son: SonRow
    regions: list[EntityRow]
    peoples: list[EntityRow]
    settlements: list[EntityRow]


@dataclass
class RichCosmos:
    home: CoreWorld
    frontiers: list[Frontier] = field(default_factory=list)
    sons: list[SonRow] = field(default_factory=list)


FRONTIERS = (
    ("Thalassa", WorldType.OCEAN, 0.6, Rarity.COMMON, (Domain.SEA, Domain.STORM)),
    ("Rimefall", WorldType.ICE, 0.2, Rarity.LEGENDARY, (Domain.WAR, Domain.DEATH)),
    ("Sandmere", WorldType.SAND, 0.1, Rarity.MYTHIC, (Domain.SUN, Domain.KNOWLEDGE)),
)
REGION_SUFFIXES = ("Reach", "Hollow", "March", "Fells", "Strand")


async def frontier(session: AsyncSession, home: CoreWorld, index: int) -> Frontier:
    name, world_type, sea, rarity, domains = FRONTIERS[index]
    world = await WorldRepository(session).create_world(
        WorldDraft(
            name=name,
            world_type=world_type,
            orbit=2.0 + index,
            terrain_seed=name.lower(),
            terrain_sea=sea,
            terrain_mountains=1.0,
            terrain_humidity=0.1,
            danger=25,
            created_epoch=1,
            star_id=home.world.star_id,
        )
    )
    son = await SonRepository(session).create(replace(son_draft(f"{name}warden", world.id, domains), rarity=rarity))
    regions = [
        await entity(
            session,
            f"{name} {suffix}",
            EntityType.REGION,
            RegionStats(breadth=55, fertility=60 + 5 * offset, magic=25, danger=20 + 5 * offset),
            world_id=world.id,
        )
        for offset, suffix in enumerate(REGION_SUFFIXES)
    ]
    tongue = await entity(session, f"{name}ic", EntityType.LANGUAGE, LanguageStats(spread=40, complexity=35, sacredness=20), world_id=world.id)
    peoples: list[EntityRow] = []
    settlements: list[EntityRow] = []
    for position, region in enumerate(regions[:3]):
        people = await entity(
            session,
            f"{name} Kin {position + 1}",
            EntityType.PEOPLE,
            PeopleStats(population=5000 + 1500 * position, martiality=40 + 10 * position, magic=20, craft=45, piety=55, prosperity=50, wealth=40),
            world_id=world.id,
            location_id=region.id,
            creator_son_id=son.id,
        )
        town = await entity(
            session,
            f"{name} Hold {position + 1}",
            EntityType.SETTLEMENT,
            SettlementStats(population=1500 + 800 * position, prosperity=45 + 10 * position, defense=30, piety=50),
            world_id=world.id,
            location_id=region.id,
            creator_son_id=son.id,
        )
        for member in (people, town):
            await bond(session, member.id, tongue.id, BondKind.SPEAKS)
        await bond(session, people.id, son.id, BondKind.WORSHIPS)
        await bond(session, town.id, people.id, BondKind.DESCENDS_FROM)
        peoples.append(people)
        settlements.append(town)
    await bond(session, peoples[0].id, peoples[2].id, BondKind.ENEMY)
    await bond(session, settlements[0].id, settlements[1].id, BondKind.TRADES_WITH)
    farming = await knowledge(session, home, f"{name} Furrows", KnowledgeBranch.AGRICULTURE)
    farming.world_id = world.id
    for member in peoples + settlements:
        await bond(session, member.id, farming.id, BondKind.KNOWS)
    await entity(session, f"{name} Lantern", EntityType.CELESTIAL, CelestialStats(brightness=55, influence=40), world_id=world.id)
    await entity(
        session,
        f"{name} Leviathan",
        EntityType.SPECIES,
        SpeciesStats(hp=180, strength=65, agility=35, intelligence=55, danger=75),
        world_id=world.id,
        location_id=regions[4].id,
        power_level=7,
    )
    await entity(
        session,
        f"{name} Grazer",
        EntityType.SPECIES,
        SpeciesStats(hp=40, strength=10, agility=40, intelligence=10, danger=10),
        world_id=world.id,
        location_id=regions[3].id,
    )
    await entity(
        session,
        f"{name} Ore",
        EntityType.RESOURCE,
        ResourceStats(abundance=70, value=55, might=20),
        world_id=world.id,
        location_id=regions[1].id,
    )
    cult = await entity(
        session, f"{name} Circle", EntityType.CULT, CultStats(followers=400, zeal=70, influence=40), world_id=world.id, location_id=regions[0].id
    )
    await bond(session, cult.id, son.id, BondKind.WORSHIPS)
    for position, town in enumerate(settlements):
        await entity(
            session,
            f"{name} Elder {position + 1}",
            EntityType.MORTAL,
            MortalStats(hp=60, strength=45, agility=40, intellect=50, charisma=60, age=30 + 5 * position, lifespan=80),
            world_id=world.id,
            location_id=town.id,
        )
    await session.flush()
    return Frontier(world=world, son=son, regions=regions, peoples=peoples, settlements=settlements)


async def seed_rich_cosmos(session: AsyncSession) -> RichCosmos:
    home = await seed_rich_world(session)
    cosmos = RichCosmos(home=home, sons=[home.son])
    for index in range(len(FRONTIERS)):
        built = await frontier(session, home, index)
        cosmos.frontiers.append(built)
        cosmos.sons.append(built.son)
        session.add(
            RouteRow(
                world_a_id=home.world.id,
                world_b_id=built.world.id,
                method=TravelMethod.ANCIENT_GATE,
                duration_epochs=1,
                danger=20,
                known=True,
                active=True,
                created_epoch=1,
            )
        )
    await session.flush()
    return cosmos
