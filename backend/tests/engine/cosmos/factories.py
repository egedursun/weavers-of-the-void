from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.sons import SonDraft, SonRepository
from aerona.db.repositories.worlds import StarDraft, WorldDraft, WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import LoreLanguage, StarType, WorldType
from aerona.domain.models.entity_stats import EntityStats, KnowledgeStats, RegionStats
from aerona.domain.models.profiles import Personality
from aerona.domain.models.stats import PassionBlock, StatBlock
from aerona.engine.context import TickContext, TickEnvironment
from aerona.engine.stats import TickStats
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules

SEED = 4242
EPOCH = 5


@dataclass
class Cosmos:
    star: StarRow
    home: WorldRow
    creator: CreatorRow


def _ignore(kind: EventKind, payload: dict[str, Any]) -> None:
    return None


def tick(session: AsyncSession, rules: Rules, epoch: int = EPOCH, phase: str = "test") -> TickContext:
    environment = TickEnvironment(rules=rules, epoch=epoch, world_seed=SEED, lore_language=LoreLanguage.ENGLISH, publish=_ignore, stats=TickStats())
    return TickContext(environment, session, phase)


def tuned(rules: Rules, namespace: str, **values: int) -> Rules:
    return replace(rules, **{namespace: replace(getattr(rules, namespace), **values)})


async def seed_cosmos(session: AsyncSession, epoch: int = EPOCH) -> Cosmos:
    repository = CosmosRepository(session)
    cosmos = await repository.create(
        CosmosDraft(name="Aerona", rng_seed=SEED, lore_language=LoreLanguage.ENGLISH, seed_idea="seed", cosmology="cosmology", tone="tone", rules=Rules())
    )
    cosmos.epoch = epoch
    creator = await repository.create_creator(CreatorDraft("Aeron", 100, 50, 10, 50, 10))
    star = await WorldRepository(session).create_star(StarDraft("Homesun", StarType.YELLOW_DWARF, 70, 0.0, 0.0, 1))
    home = await make_world(session, "Orvael", star_id=star.id)
    cosmos.primary_world_id = home.id
    await session.flush()
    return Cosmos(star, home, creator)


async def make_world(
    session: AsyncSession, name: str, world_type: WorldType = WorldType.ORDINARY, star_id: int | None = None, created_epoch: int = 1
) -> WorldRow:
    return await WorldRepository(session).create_world(
        WorldDraft(
            name=name,
            world_type=world_type,
            orbit=1.0,
            terrain_seed=f"{name}:seed",
            terrain_sea=0.5,
            terrain_mountains=1.0,
            terrain_humidity=0.0,
            danger=20,
            created_epoch=created_epoch,
            star_id=star_id,
        )
    )


async def make_entity(
    session: AsyncSession,
    name: str,
    entity_type: EntityType,
    stats: EntityStats,
    *,
    world_id: int,
    location_id: int | None = None,
    power: int = 3,
    **extra: Any,
) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=f"The {entity_type.value} {name}.",
            stats=stats,
            power_level=power,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=world_id,
            location_id=location_id,
            **extra,
        )
    )


async def make_region(session: AsyncSession, name: str, world_id: int, **stats: int) -> EntityRow:
    return await make_entity(session, name, EntityType.REGION, RegionStats(**stats), world_id=world_id)


async def teach(session: AsyncSession, entity: EntityRow, branch: KnowledgeBranch) -> EntityRow:
    knowledge = await make_entity(
        session, f"{branch.value.title()} Lore {entity.id}", EntityType.KNOWLEDGE, KnowledgeStats(level=1), world_id=entity.world_id, knowledge_branch=branch
    )
    await BondRepository(session).connect(BondDraft(entity.id, knowledge.id, BondKind.KNOWS, 1))
    return knowledge


async def make_son(
    session: AsyncSession,
    name: str,
    world_id: int | None,
    *,
    stats: int = 50,
    rarity: Rarity = Rarity.RARE,
    domains: tuple[Domain, Domain] = (Domain.SEA, Domain.SALT),
) -> SonRow:
    return await SonRepository(session).create(
        SonDraft(
            name=name,
            title="the Tester",
            rarity=rarity,
            domains=domains,
            stats=StatBlock.uniform(stats),
            passions=PassionBlock(loyalty=60, ambition=40, wrath=20, mercy=50),
            personality=Personality(temperament="calm"),
            existence=60,
            hp=100,
            essence=100,
            birth_epoch=1,
            current_world_id=world_id,
        )
    )


async def make_route(
    session: AsyncSession,
    first: int,
    second: int,
    method: TravelMethod = TravelMethod.ANCIENT_GATE,
    *,
    known: bool = True,
    active: bool = True,
    danger: int = 0,
    duration: int = 1,
) -> RouteRow:
    route = RouteRow(world_a_id=first, world_b_id=second, method=method, duration_epochs=duration, danger=danger, known=known, active=active, created_epoch=1)
    session.add(route)
    await session.flush()
    return route
