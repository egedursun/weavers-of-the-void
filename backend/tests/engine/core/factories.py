from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.model import ElevationClass, RegionRecord
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.sons import SonDraft, SonRepository
from aerona.db.repositories.worlds import StarDraft, WorldDraft, WorldRepository
from aerona.db.tables.celestial import WorldMapRow, WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.lore import ChronicleRow, LexemeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import FeedCategory, PartOfSpeech
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityType, MortalRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.enums.world import LoreLanguage, StarType, WorldType
from aerona.domain.models.entity_stats import (
    EntityStats,
    ItemStats,
    KnowledgeStats,
    LanguageStats,
    LawStats,
    LegendStats,
    MortalStats,
    NaturalLawStats,
    PeopleStats,
    RegionStats,
    ResourceStats,
    SettlementStats,
    SpeciesStats,
    SpiritStats,
    TraditionStats,
)
from aerona.domain.models.profiles import Personality
from aerona.domain.models.stats import PassionBlock, StatBlock
from aerona.engine.context import TickContext
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

WORLD_SEED = 20261031
LANGUAGE_WORDS = (("vael", "water"), ("toren", "fire"), ("mirak", "earth"), ("sola", "mother"), ("kesh", "sky"), ("dumar", "road"), ("orin", "bread"))


@dataclass
class CoreWorld:
    cosmos: CosmosRow
    creator: CreatorRow
    world: WorldRow
    son: SonRow
    regions: list[EntityRow]
    people: EntityRow
    language: EntityRow
    species: EntityRow
    extra: dict[str, EntityRow] = field(default_factory=dict)


def region_record(region_id: int, neighbours: Sequence[int]) -> RegionRecord:
    return RegionRecord(
        id=region_id,
        parent_id=None,
        top_level_id=region_id,
        depth=0,
        is_water=False,
        seed=None,
        anchor=None,
        centroid=None,
        size=10,
        coastal=False,
        mean_elevation=0.5,
        elevation_class=ElevationClass.PLAIN,
        climate=[],
        neighbours=list(neighbours),
        bordering=list(neighbours),
    )


def son_draft(name: str, world_id: int | None, domains: tuple[Domain, Domain] = (Domain.HARVEST, Domain.LIGHT)) -> SonDraft:
    return SonDraft(
        name=name,
        title="the Patient",
        rarity=Rarity.RARE,
        domains=domains,
        stats=StatBlock.uniform(50),
        passions=PassionBlock(loyalty=60, ambition=40, wrath=20, mercy=50),
        personality=Personality(temperament="calm"),
        existence=60,
        hp=100,
        essence=50,
        birth_epoch=1,
        current_world_id=world_id,
    )


async def entity(
    session: AsyncSession,
    name: str,
    entity_type: EntityType,
    stats: EntityStats,
    *,
    world_id: int,
    location_id: int | None = None,
    origin: EntityOrigin = EntityOrigin.SON,
    creator_son_id: int | None = None,
    birth_epoch: int = 1,
    power_level: int = 3,
    mortal_role: MortalRole | None = None,
) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=f"The {entity_type.value} called {name}.",
            stats=stats,
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


async def bond(session: AsyncSession, source: int, target: int, kind: BondKind, epoch: int = 1) -> None:
    await BondRepository(session).connect(BondDraft(source, target, kind, epoch))


async def mortal(session: AsyncSession, name: str, world: CoreWorld, location_id: int | None, **stats: int) -> EntityRow:
    values = {"hp": 60, "strength": 40, "agility": 40, "intellect": 40, "charisma": 40, "age": 25, "lifespan": 70} | stats
    return await entity(session, name, EntityType.MORTAL, MortalStats(**values), world_id=world.world.id, location_id=location_id)


async def seed_core_world(session: AsyncSession, rules: Rules | None = None) -> CoreWorld:
    cosmos = await CosmosRepository(session).create(
        CosmosDraft(
            name="Aerona",
            rng_seed=WORLD_SEED,
            lore_language=LoreLanguage.ENGLISH,
            seed_idea="A quiet test cosmos.",
            cosmology="Many layered worlds.",
            tone="calm",
            rules=rules or Rules(),
        )
    )
    creator = await CosmosRepository(session).create_creator(
        CreatorDraft(name="Aeron", essence=150, mood_contentment=50, mood_anger=10, mood_interest=50, mood_loneliness=20)
    )
    worlds = WorldRepository(session)
    star = await worlds.create_star(StarDraft("Velar Sun", StarType.YELLOW_DWARF, 70, 0.0, 0.0, 1))
    world = await worlds.create_world(
        WorldDraft(
            name="Velar",
            world_type=WorldType.ORDINARY,
            orbit=1.0,
            terrain_seed="velar",
            terrain_sea=0.4,
            terrain_mountains=1.0,
            terrain_humidity=0.0,
            danger=20,
            created_epoch=1,
            star_id=star.id,
        )
    )
    cosmos.primary_world_id = world.id
    son = await SonRepository(session).create(son_draft("Ithren", world.id))
    fertility = (70, 85, 60, 45)
    regions = [
        await entity(session, name, EntityType.REGION, RegionStats(breadth=60, fertility=value, magic=20, danger=20), world_id=world.id)
        for name, value in zip(("Amberreach", "Greenvale", "Stonefold", "Ashmere"), fertility, strict=True)
    ]
    ids = [region.id for region in regions]
    chain = {ids[0]: [ids[1]], ids[1]: [ids[0], ids[2]], ids[2]: [ids[1], ids[3]], ids[3]: [ids[2]]}
    session.add(
        WorldMapRow(
            world_id=world.id,
            generator_version=1,
            epoch=1,
            geometry={"regions": [region_record(key, value).model_dump(mode="json") for key, value in chain.items()]},
        )
    )
    language = await entity(session, "Velari", EntityType.LANGUAGE, LanguageStats(spread=40, complexity=30, sacredness=20), world_id=world.id)
    session.add_all(
        LexemeRow(
            language_entity_id=language.id,
            word=word,
            meaning=meaning,
            part_of_speech=PartOfSpeech.NOUN,
            added_by_kind=ActorKind.SON,
            added_by_node_id=son.id,
            epoch=1,
        )
        for word, meaning in LANGUAGE_WORDS
    )
    people = await entity(
        session,
        "Kethrani",
        EntityType.PEOPLE,
        PeopleStats(population=6000, martiality=40, magic=20, craft=55, piety=60, prosperity=55, wealth=40),
        world_id=world.id,
        location_id=regions[0].id,
        creator_son_id=son.id,
    )
    await bond(session, people.id, language.id, BondKind.SPEAKS)
    await bond(session, people.id, son.id, BondKind.WORSHIPS)
    species = await entity(
        session,
        "Duskhorn",
        EntityType.SPECIES,
        SpeciesStats(hp=80, strength=40, agility=50, intelligence=20, danger=30),
        world_id=world.id,
        location_id=regions[2].id,
    )
    await session.flush()
    return CoreWorld(cosmos=cosmos, creator=creator, world=world, son=son, regions=regions, people=people, language=language, species=species)


async def add_empty_world(session: AsyncSession, name: str = "Orun") -> tuple[WorldRow, list[EntityRow]]:
    worlds = WorldRepository(session)
    world = await worlds.create_world(
        WorldDraft(
            name=name,
            world_type=WorldType.ORDINARY,
            orbit=2.0,
            terrain_seed=name.lower(),
            terrain_sea=0.3,
            terrain_mountains=1.0,
            terrain_humidity=0.2,
            danger=10,
            created_epoch=1,
        )
    )
    regions = [
        await entity(session, f"{name} {suffix}", EntityType.REGION, RegionStats(breadth=50, fertility=75, magic=10, danger=10), world_id=world.id)
        for suffix in ("Meadow", "Shore")
    ]
    first, second = regions
    records = [region_record(first.id, [second.id]), region_record(second.id, [first.id])]
    session.add(WorldMapRow(world_id=world.id, generator_version=1, epoch=1, geometry={"regions": [record.model_dump(mode="json") for record in records]}))
    await session.flush()
    return world, regions


async def settlement(session: AsyncSession, name: str, world: CoreWorld, region: EntityRow, population: int = 1200, **stats: int) -> EntityRow:
    values = {"population": population, "prosperity": 50, "defense": 30, "piety": 50} | stats
    return await entity(session, name, EntityType.SETTLEMENT, SettlementStats(**values), world_id=world.world.id, location_id=region.id)


async def knowledge(session: AsyncSession, world: CoreWorld, name: str, branch: KnowledgeBranch) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=EntityType.KNOWLEDGE,
            description=f"The knowledge of {name}.",
            stats=KnowledgeStats(level=2, spread=30),
            power_level=2,
            origin=EntityOrigin.SON,
            birth_epoch=1,
            world_id=world.world.id,
            knowledge_branch=branch,
            split_title=False,
        )
    )


async def natural_law(session: AsyncSession, world: CoreWorld, name: str, law: NaturalLaw) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=EntityType.NATURAL_LAW,
            description=f"The law of {name}.",
            stats=NaturalLawStats(),
            power_level=5,
            origin=EntityOrigin.SON,
            birth_epoch=1,
            world_id=world.world.id,
            natural_law=law,
            split_title=False,
        )
    )


async def seed_rich_world(session: AsyncSession) -> CoreWorld:
    world = await seed_core_world(session)
    regions = world.regions
    town = await settlement(session, "Harrowmere", world, regions[1], population=4200, prosperity=70)
    port = await settlement(session, "Saltgate", world, regions[3], population=3500, prosperity=20)
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    await bond(session, port.id, world.people.id, BondKind.DESCENDS_FROM)
    await bond(session, town.id, world.language.id, BondKind.SPEAKS)
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    for name, branch in (
        ("Ember Lore", KnowledgeBranch.MAGIC),
        ("Ink Craft", KnowledgeBranch.WRITING),
        ("Root Healing", KnowledgeBranch.MEDICINE),
        ("Stone Art", KnowledgeBranch.ARCHITECTURE),
    ):
        lore = await knowledge(session, world, name, branch)
        await bond(session, town.id, lore.id, BondKind.KNOWS)
        await bond(session, world.people.id, lore.id, BondKind.KNOWS)
    sage = await mortal(session, "Ilvane", world, town.id, intellect=80, strength=70, agility=60, charisma=75, age=40, lifespan=90)
    lover = await mortal(session, "Corwen", world, town.id, intellect=50, age=30)
    await bond(session, sage.id, lover.id, BondKind.LOVES)
    await bond(session, sage.id, town.id, BondKind.RULES)
    lore_ids = [lore.id for lore in await EntityRepository(session).canon(EntityType.KNOWLEDGE)]
    for lore_id in lore_ids:
        await bond(session, sage.id, lore_id, BondKind.KNOWS)
    beast = await entity(
        session,
        "Gravemaw",
        EntityType.SPECIES,
        SpeciesStats(hp=200, strength=70, agility=40, intelligence=75, danger=80),
        world_id=world.world.id,
        location_id=regions[1].id,
        power_level=6,
    )
    blade = await entity(
        session, "Dawnsplitter", EntityType.ITEM, ItemStats(damage=60, protection=10, might=30, curse=70), world_id=world.world.id, location_id=town.id
    )
    await bond(session, sage.id, blade.id, BondKind.OWNS)
    ore = await entity(
        session, "Brightvein", EntityType.RESOURCE, ResourceStats(abundance=60, value=50, might=20), world_id=world.world.id, location_id=regions[1].id
    )
    await bond(session, town.id, ore.id, BondKind.OWNS)
    tale = await entity(session, "The Drowned Spring", EntityType.LEGEND, LegendStats(spread=90), world_id=world.world.id, birth_epoch=1)
    await bond(session, tale.id, regions[1].id, BondKind.TELLS_OF)
    await bond(session, town.id, tale.id, BondKind.TELLS_OF)
    feast = await entity(session, "Lantern Feast", EntityType.TRADITION, TraditionStats(spread=30, rigidity=40), world_id=world.world.id)
    await bond(session, town.id, feast.id, BondKind.CELEBRATES)
    await entity(
        session,
        "Weeping Shade",
        EntityType.SPIRIT,
        SpiritStats(strength=40, unrest=80),
        world_id=world.world.id,
        location_id=regions[1].id,
        origin=EntityOrigin.ENGINE,
    )
    await entity(session, "Iron Code", EntityType.LAW, LawStats(rigidity=50, justice=80), world_id=world.world.id, location_id=town.id)
    await add_flag(session, port.id, EntityFlag.CURSED)
    world.extra.update({"town": town, "port": port, "sage": sage, "lover": lover, "beast": beast, "blade": blade, "ore": ore, "tale": tale, "feast": feast})
    await session.flush()
    return world


async def add_flag(session: AsyncSession, entity_id: int, flag: EntityFlag) -> None:
    await EntityRepository(session).add_flag(entity_id, flag, 1)


def tuned_rules(**namespaces: dict[str, int]) -> Rules:
    rules = Rules()
    for namespace, values in namespaces.items():
        rules = replace(rules, **{namespace: replace(getattr(rules, namespace), **values)})
    return rules


async def tell_history(ctx: TickContext, text: str, *, ids: Sequence[int] = (), feed: FeedCategory | None = None) -> ChronicleRow:
    written = await record(ctx, "player.history", roles={IncidentRole.SUBJECT: tuple(ids)}, facts={"account": text}, feed=feed)
    return written.row


async def surveyed(session: AsyncSession, world: CoreWorld) -> None:
    if await session.get(RegionEnvironmentRow, world.regions[0].id) is None:
        await environment_survey(await manual_context(session, "survey", rules=tuned_rules()))
