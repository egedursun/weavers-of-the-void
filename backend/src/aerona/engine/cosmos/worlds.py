from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.worlds import WORLD_TYPES
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, Discovery, WorldType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import cosmography_of
from aerona.engine.cosmos.routes import JourneyView, RouteBook, RouteStatus, SkyCalendar, journey_views
from aerona.engine.cosmos.world_types import is_mirror
from aerona.engine.primitives.physics import WorldPhysics, world_physics
from aerona.rules.registry import Rules

LIVING_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL, EntityType.SPECIES})
POPULATED_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})


async def require_world(session: AsyncSession, world_id: int) -> WorldRow:
    world = await session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    return world


async def _mortal_count(session: AsyncSession, world_id: int) -> int:
    statement = select(func.count()).select_from(EntityRow).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.MORTAL)
    return int(await session.scalar(statement) or 0)


async def assign_mirror_twin(session: AsyncSession, world: WorldRow) -> WorldRow | None:
    if world.mirror_twin_id is not None:
        return await session.get(WorldRow, world.mirror_twin_id)
    repository = WorldRepository(session)
    star = await repository.root_star_id(world)
    ranked: list[tuple[int, int, int, WorldRow]] = []
    for other in await repository.reachable_worlds():
        if other.id == world.id:
            continue
        same_star = star is not None and await repository.root_star_id(other) == star
        ranked.append((0 if same_star else 1, -await _mortal_count(session, other.id), other.id, other))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[:3])
    world.mirror_twin_id = ranked[0][3].id
    await session.flush()
    return ranked[0][3]


async def pair_mirrors(session: AsyncSession) -> int:
    paired = 0
    for world in await WorldRepository(session).all_worlds():
        if is_mirror(world.world_type) and world.mirror_twin_id is None and await assign_mirror_twin(session, world) is not None:
            paired += 1
    return paired


async def set_mirror_twin(session: AsyncSession, world_id: int, twin_id: int | None) -> WorldRow:
    world = await require_world(session, world_id)
    if twin_id is not None:
        if twin_id == world_id:
            raise ValidationFailedError("A mirror world cannot be its own twin.")
        await require_world(session, twin_id)
    world.mirror_twin_id = twin_id
    await session.flush()
    return world


async def align_moons(session: AsyncSession) -> int:
    repository = WorldRepository(session)
    moved = 0
    for world in await repository.all_worlds():
        if world.parent_world_id is None:
            continue
        root = await repository.root_star_id(world)
        if world.star_id != root:
            world.star_id = root
            moved += 1
    await session.flush()
    return moved


async def declare_holy_world(ctx: TickContext, son: SonRow, world: WorldRow, *, automatic: bool = False) -> str:
    previous = await ctx.session.get(SonRow, world.patron_son_id) if world.patron_son_id is not None else None
    trampled = previous is not None and previous.id != son.id and previous.status is not SonStatus.DEAD
    if trampled and previous is not None:
        await SonRepository(ctx.session).change_relation(son.id, previous.id, -ctx.rules.pantheon.holy_world_take_relation)
    world.patron_son_id = son.id
    world.patron_automatic = automatic
    suffix = f"; trampling {previous.name}'s claim" if trampled and previous is not None else ""
    text = f"{son.name} declared {world.name} their holy world{suffix}."
    await ctx.chronicle(ChronicleKind.COSMIC, text, template_key="cosmos.holy_world", son_id=son.id, world_id=world.id, feed_category=FeedCategory.WORLD)
    await ctx.session.flush()
    return text


async def forget_world(ctx: TickContext, world_id: int, by: str) -> str:
    session = ctx.session
    cosmos = await CosmosRepository(session).require_cosmos()
    primary = cosmos.primary_world_id or await CosmosRepository(session).first_world_id()
    if world_id == primary:
        raise ValidationFailedError("You cannot forget your first world.")
    world = await require_world(session, world_id)
    repository = WorldRepository(session)
    await repository.set_discovery(world, Discovery.FORGOTTEN)
    for route in await repository.routes_touching(world.id, active_only=True):
        route.active = False
    for son in await session.scalars(select(SonRow).where(SonRow.current_world_id == world.id)):
        son.current_world_id = primary
    text = f"{by} forgot {world.name}. Its routes closed, and it survives only in tales."
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, text, template_key="cosmos.world_forgotten", world_id=world.id, feed_category=FeedCategory.WORLD)
    await session.flush()
    return text


@dataclass(frozen=True)
class WorldCounts:
    regions: int = 0
    peoples: int = 0
    settlements: int = 0
    living: int = 0
    population: int = 0
    outer: int = 0


@dataclass(frozen=True)
class WorldSummary:
    world: WorldRow
    type_name: str
    counts: WorldCounts
    son_ids: tuple[int, ...]
    physics: WorldPhysics


@dataclass(frozen=True)
class QuestAvailability:
    dead_star: bool
    sealed_gate: bool
    archive: bool
    expel_outer: bool


@dataclass(frozen=True)
class RouteSummary:
    route: RouteRow
    status: RouteStatus


@dataclass(frozen=True)
class CosmosOverview:
    stars: list[StarRow]
    worlds: list[WorldSummary]
    region_targets: list[EntityRow]
    community_targets: list[EntityRow]
    quests: QuestAvailability
    routes: list[RouteSummary]
    calendar: SkyCalendar
    journeys: list[JourneyView]
    types: dict[WorldType, str] = field(default_factory=dict)


async def world_counts(session: AsyncSession) -> dict[int, WorldCounts]:
    statement = (
        select(EntityRow.world_id, EntityRow.entity_type, func.count(), func.sum(func.json_extract(EntityRow.stats, "$.population")))
        .where(EntityRow.status == EntityStatus.CANON)
        .group_by(EntityRow.world_id, EntityRow.entity_type)
    )
    raw: dict[int, dict[EntityType, tuple[int, int]]] = defaultdict(dict)
    for world_id, entity_type, count, population in await session.execute(statement):
        raw[world_id][entity_type] = (int(count), int(population or 0))
    counts: dict[int, WorldCounts] = {}
    for world_id, by_type in raw.items():
        counts[world_id] = WorldCounts(
            regions=by_type.get(EntityType.REGION, (0, 0))[0],
            peoples=by_type.get(EntityType.PEOPLE, (0, 0))[0],
            settlements=by_type.get(EntityType.SETTLEMENT, (0, 0))[0],
            living=sum(by_type.get(kind, (0, 0))[0] for kind in LIVING_TYPES),
            population=sum(by_type.get(kind, (0, 0))[1] for kind in POPULATED_TYPES),
            outer=by_type.get(EntityType.OUTER_BEING, (0, 0))[0],
        )
    return counts


async def quest_availability(session: AsyncSession, book: RouteBook) -> QuestAvailability:
    dead = await session.scalar(select(StarRow.id).where(StarRow.star_type.in_(list(EXTINGUISHED_STAR_TYPES))).limit(1)) is not None
    sealed = any(
        not route.active
        and route.temp_closed_until_epoch is None
        and route.temp_open_until_epoch is None
        and route.world_a_id not in book.forgotten
        and route.world_b_id not in book.forgotten
        for route in book.routes
    )
    archive_statement = select(EntityRow.id).where(
        EntityRow.engine_kind == EngineKind.COSMIC_ARCHIVE, EntityRow.status == EntityStatus.CANON, EntityRow.world_id.not_in(book.forgotten or {-1})
    )
    archive = await session.scalar(archive_statement.limit(1)) is not None
    outer_statement = select(EntityRow.id).where(EntityRow.entity_type == EntityType.OUTER_BEING, EntityRow.status == EntityStatus.CANON)
    outer = await session.scalar(outer_statement.limit(1)) is not None
    return QuestAvailability(dead, sealed, archive, outer)


async def cosmos_overview(session: AsyncSession, rules: Rules, epoch: int) -> CosmosOverview:
    book = await RouteBook.load(session, rules, epoch)
    counts = await world_counts(session)
    sons_by_world: dict[int, list[int]] = defaultdict(list)
    for son in await SonRepository(session).living():
        if son.current_world_id is not None:
            sons_by_world[son.current_world_id].append(son.id)
    star_rows = list(await session.scalars(select(StarRow).order_by(StarRow.id)))
    stars = {star.id: star for star in star_rows}
    ladder = await cosmography_of(session)
    worlds = [
        WorldSummary(
            world,
            WORLD_TYPES[world.world_type].label,
            counts.get(world.id, WorldCounts()),
            tuple(sons_by_world.get(world.id, [])),
            world_physics(rules, world, stars.get(world.star_id) if world.star_id is not None else None, ladder.pull(rules, ladder.place_world(world))),
        )
        for world in await WorldRepository(session).all_worlds()
    ]
    land = select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_([EntityType.REGION, EntityType.PLACE]))
    communities = select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_([*COMMUNITY_TYPES, EntityType.MORTAL]))
    return CosmosOverview(
        stars=star_rows,
        worlds=worlds,
        region_targets=list(await session.scalars(land.order_by(EntityRow.name))),
        community_targets=list(await session.scalars(communities.order_by(EntityRow.name))),
        quests=await quest_availability(session, book),
        routes=[RouteSummary(route, book.status(route)) for route in book.routes],
        calendar=book.calendar,
        journeys=await journey_views(session, rules.travel.list_expeditions),
        types={world_type: spec.label for world_type, spec in WORLD_TYPES.items()},
    )
