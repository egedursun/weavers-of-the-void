from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.frontier import frontier_position
from aerona.catalog.civilization import unlocked
from aerona.constants.cosmos import SUMMARY_CHRONICLE_LINES, SUMMARY_INTUITION_LINES
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import DeferredStepRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.routes import HorizonIntuitionRow, RouteRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.epoch import DeferredStepKind, DeferredStepStatus
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.society import Commodity, KnowledgeBranch
from aerona.domain.enums.travel import HorizonStatus, TravelMethod, VehicleKind
from aerona.domain.enums.world import Discovery
from aerona.domain.models.entity_stats import EntityStats, PlaceStats, RegionStats, SettlementStats, VesselStats
from aerona.engine.body.book import factor
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import hidden_sky
from aerona.engine.cosmos.routes import RouteSpec, has_tamed_mount, open_route
from aerona.engine.cosmos.vessels import set_vessel_kind
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.capacity import CapacityModel
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.society import stock
from aerona.engine.primitives.stats import headcount, put_stat, stat, stat_or
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

KNOWLEDGE_FOR_EXPLORING = frozenset({KnowledgeBranch.SEAFARING, KnowledgeBranch.PATHFINDING, KnowledgeBranch.ASTRONOMY, KnowledgeBranch.SKY_NAVIGATION})
LAND_COMMUNITIES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
SEEKER_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})
INTELLECT_KEY = "intellect"
AGILITY_KEY = "agility"
INFLUENCE_KEY = "influence"
PROSPERITY_KEY = "prosperity"
PIETY_KEY = "piety"
POPULATION_KEY = "population"
COSMIC_SEARCH_HOW = "searching with all they knew"


class Reason(StrEnum):
    NARROW = "narrow"
    HUNGER = "hunger"
    POVERTY = "poverty"
    EXPLORER = "explorer"
    KNOWLEDGE = "knowledge"
    SPIRIT = "spirit"


PHRASES: dict[Reason, tuple[str, ...]] = {
    Reason.NARROW: ("when their homeland grew too small", "when their lands grew crowded", "when they no longer fit their lands"),
    Reason.HUNGER: ("when their food ran short", "when hunger came", "when famine struck"),
    Reason.POVERTY: ("when poverty pressed", "when they grew poor", "when poverty spread through the homeland"),
    Reason.EXPLORER: ("led by {name}", "following {name}", "when {name} went ahead of them"),
    Reason.KNOWLEDGE: ("trusting what they knew of travel", "with old knowledge of the way", "guided by their learning"),
    Reason.SPIRIT: ("unable to stay still", "giving in to curiosity", "with the curiosity within"),
}
NEED_REASONS = (Reason.NARROW, Reason.HUNGER, Reason.POVERTY)


def exploration_sentence(reasons: list[Reason], variant: int, explorer_name: str | None = None) -> str:
    def phrase(reason: Reason) -> str:
        options = PHRASES[reason]
        return options[variant % len(options)].format(name=explorer_name or "an explorer")

    needs = " and ".join(phrase(reason) for reason in NEED_REASONS if reason in reasons)
    parts = [needs] if needs else []
    if Reason.EXPLORER in reasons:
        parts.append(phrase(Reason.EXPLORER))
    if Reason.SPIRIT in reasons:
        parts.append(phrase(Reason.SPIRIT))
    if Reason.KNOWLEDGE in reasons:
        parts.append(phrase(Reason.KNOWLEDGE))
    return " ".join(parts)


@dataclass(frozen=True)
class LandMeasure:
    world_id: int
    regions: int
    places: int
    communities: int
    crowded: tuple[tuple[int, int], ...]
    ratio: float
    narrow: bool


async def land_measure(session: AsyncSession, rules: Rules, world_id: int, atlas: RegionAtlas | None = None) -> LandMeasure:
    regions = await canon(session, [EntityType.REGION], world_id)
    places = await canon(session, [EntityType.PLACE], world_id)
    communities = await canon(session, LAND_COMMUNITIES, world_id)
    region_atlas = atlas or await RegionAtlas.load(session)
    per_region = Counter(region for region in (region_atlas.top_region(item.id) for item in communities) if region is not None)
    threshold = rules.exploration.crowded_communities_per_region
    crowded = tuple(sorted(((region, count) for region, count in per_region.items() if count >= threshold), key=lambda item: -item[1]))
    ratio = round(len(communities) / max(1, len(regions)), 2)
    return LandMeasure(world_id, len(regions), len(places), len(communities), crowded, ratio, not regions or ratio >= threshold)


def is_explorer(rules: Rules, entity: EntityRow, mobility: float = 1.0) -> bool:
    if entity.entity_type is not EntityType.MORTAL:
        return False
    return (stat_or(entity, INTELLECT_KEY, 0) + stat_or(entity, AGILITY_KEY, 0)) * mobility >= rules.exploration.explorer_threshold


async def explores(ctx: TickContext, entity: EntityRow) -> bool:
    return is_explorer(ctx.rules, entity, await factor(ctx.session, entity.id, Capacity.MOBILITY))


@dataclass
class Pressure:
    pct: int
    reasons: list[Reason]
    explorer: EntityRow | None


@dataclass
class ExplorationScene:
    atlas: RegionAtlas
    knowledge: KnowledgeMap
    capacity: CapacityModel
    explorers: list[EntityRow]
    away: set[int] = field(default_factory=set)

    @classmethod
    async def load(cls, ctx: TickContext) -> "ExplorationScene":
        explorers = [mortal for mortal in await canon(ctx.session, [EntityType.MORTAL]) if await explores(ctx, mortal)]
        statement = select(BondRow.source_node_id).where(BondRow.kind == BondKind.DISCOVERED, BondRow.epoch == ctx.epoch)
        away = set(await ctx.session.scalars(statement))
        return cls(await RegionAtlas.load(ctx.session), await KnowledgeMap.load(ctx.session), await CapacityModel.load(ctx.session, ctx.rules), explorers, away)

    def occupancy(self, entity: EntityRow, communities: list[EntityRow]) -> int:
        loads = self.capacity.build_loads(communities)
        key = self.capacity.region_key(entity)
        load = loads.get(key) or self.capacity.build_loads([entity])[key]
        capacity = self.capacity.capacity(load, entity, self.capacity.effective_fertility(entity))
        return round(load.population / max(1.0, capacity) * PERCENT)

    def local_explorer(self, entity: EntityRow) -> EntityRow | None:
        region = self.atlas.top_region(entity.id)
        return next(
            (mortal for mortal in self.explorers if mortal.id not in self.away and region is not None and self.atlas.top_region(mortal.id) == region), None
        )


async def exploration_pressure(ctx: TickContext, scene: ExplorationScene, entity: EntityRow, communities: list[EntityRow]) -> Pressure:
    settings = ctx.rules.exploration
    pct = settings.base_chance
    reasons: list[Reason] = []
    explorer: EntityRow | None = None
    if entity.entity_type in COMMUNITY_TYPES:
        if entity.entity_type in LAND_COMMUNITIES and scene.occupancy(entity, communities) >= settings.crowded_fill_pct:
            pct += settings.crowded_bonus_pct
            reasons.append(Reason.NARROW)
        hungry = entity.entity_type in LAND_COMMUNITIES and await stock(ctx.session, ctx.rules, entity.id, Commodity.FOOD) < ctx.rules.world_effects.hungry_food
        poor = stat_or(entity, PROSPERITY_KEY, ctx.rules.travel.default_prosperity) < settings.poor_prosperity
        if hungry or poor:
            pct += settings.hungry_bonus_pct
            reasons.append(Reason.HUNGER if hungry else Reason.POVERTY)
        explorer = scene.local_explorer(entity)
        if explorer is not None:
            pct += settings.explorer_bonus_pct
            reasons.append(Reason.EXPLORER)
    elif await explores(ctx, entity):
        pct += settings.explorer_bonus_pct
        reasons.append(Reason.SPIRIT)
    if scene.knowledge.branches(entity.id) & KNOWLEDGE_FOR_EXPLORING:
        pct += settings.knowledge_bonus_pct
        reasons.append(Reason.KNOWLEDGE)
    return Pressure(clamp_percent(pct), reasons, explorer)


@dataclass(frozen=True)
class LandSearch:
    world_id: int
    explorer: EntityRow | None = None
    leader: EntityRow | None = None
    foreign_god: ForeignGodRow | None = None
    near: EntityRow | None = None
    kind: EntityType | None = None
    reason: str | None = None
    pioneers: bool = True
    narrow: bool = False


@dataclass(frozen=True)
class LandResult:
    land: EntityRow
    kind: EntityType
    pioneer: EntityRow | None
    text: str


def land_stats(ctx: TickContext, kind: EntityType, rng: SeededRandom) -> EntityStats:
    settings = ctx.rules.exploration

    def rolled(base: int, die: int) -> int:
        return clamp_percent(base + rng.die(die))

    fertility = rolled(settings.land_fertility_base, settings.land_fertility_die)
    danger = rolled(settings.land_danger_base, settings.land_danger_die)
    if kind is EntityType.REGION:
        return RegionStats(
            breadth=rolled(settings.land_stat_base, settings.land_stat_die),
            danger=danger,
            fertility=fertility,
            magic=rolled(settings.land_stat_base, settings.land_stat_die),
        )
    return PlaceStats(danger=danger, fertility=fertility, mystery=rolled(settings.land_stat_base, settings.land_stat_die))


async def place_region(ctx: TickContext, world_id: int, source: EntityRow | None, atlas: RegionAtlas) -> EntityRow | None:
    regions = {region.id: region for region in await canon(ctx.session, [EntityType.REGION], world_id)}
    candidate_ids = [source.id, *atlas.neighbour_regions(source.id)] if source is not None else list(regions)
    candidates = [regions[item] for item in candidate_ids if item in regions and not regions[item].is_water and not atlas.is_water(item)]
    if not candidates:
        return None
    statement = (
        select(EntityRow.location_id, func.count())
        .where(EntityRow.entity_type == EntityType.PLACE, EntityRow.status == EntityStatus.CANON)
        .group_by(EntityRow.location_id)
    )
    places = {location: count for location, count in await ctx.session.execute(statement)}
    return min(candidates, key=lambda region: (places.get(region.id, 0), region.id))


async def position_region(ctx: TickContext, region: EntityRow, source: EntityRow | None) -> None:
    if region.map_x is not None or source is None or source.map_x is None or source.map_y is None:
        return
    others = [
        (item.map_x, item.map_y)
        for item in await canon(ctx.session, [EntityType.REGION], region.world_id)
        if item.map_x is not None and item.map_y is not None and item.id != region.id
    ]
    rng = ctx.rng(seed_of("frontier", region.id))
    region.map_x, region.map_y = frontier_position(
        (source.map_x, source.map_y), [(float(x), float(y)) for x, y in others if x is not None and y is not None], rng.random, ctx.rules
    )


async def _land_name(ctx: TickContext, search: LandSearch, kind: EntityType, who: str) -> tuple[str, bool]:
    if search.explorer is not None:
        derived = await Namer(ctx.session, ctx.rules).from_speaker(
            search.explorer.id, seed_of(search.explorer.id, ctx.epoch, "exploration", kind.value), NameKind.PLACE
        )
        if derived is not None:
            return derived, True
    return (f"{who} Discovery" if kind is EntityType.PLACE else f"{who} Beyond"), False


async def find_land(ctx: TickContext, search: LandSearch) -> LandResult | None:
    rng = ctx.rng(seed_of("land", search.world_id, search.explorer.id if search.explorer else 0))
    atlas = await RegionAtlas.load(ctx.session)
    world = await ctx.session.get(WorldRow, search.world_id)
    if world is None:
        return None
    source_id = atlas.top_region(search.explorer.id) if search.explorer is not None and search.explorer.world_id == world.id else None
    source = await ctx.session.get(EntityRow, source_id) if source_id is not None else search.near
    kind = search.kind or (EntityType.REGION if rng.chance(ctx.rules.exploration.new_region_pct) else EntityType.PLACE)
    parent = await place_region(ctx, world.id, source, atlas) if kind is EntityType.PLACE else None
    if kind is EntityType.PLACE and parent is None:
        return None
    who = search.explorer.name if search.explorer else search.foreign_god.name if search.foreign_god else world.name
    name, derived = await _land_name(ctx, search, kind, who)
    if search.foreign_god is not None:
        how = f"{search.foreign_god.name} raised it in the world {world.name}"
    else:
        how = f"{who}{', ' + search.reason if search.reason else ''} set out into unknown lands and found it"
    where = f"a place inside {parent.name} unknown until that day" if parent is not None else "a new region not on the map"
    flags = (EntityFlag.DISCOVERY, EntityFlag.NAME_FROM_LANGUAGE) if derived else (EntityFlag.DISCOVERY,)
    land = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=name,
            entity_type=kind,
            body=f"{how}: {where}.",
            stats=land_stats(ctx, kind, rng),
            power=ctx.rules.exploration.land_power,
            world_id=world.id,
            location_id=parent.id if parent is not None else None,
            subtype="discovered place" if kind is EntityType.PLACE else "discovered lands",
            flags=flags,
        ),
    )
    if kind is EntityType.REGION:
        await position_region(ctx, land, source)
    await _discovery_bonds(ctx, search, land)
    pioneer = await _maybe_pioneers(ctx, search, land, rng)
    text = _land_text(search, land, parent, world, pioneer)
    await note(ctx, text, key="exploration.land_found", ids=[item.id for item in (search.explorer, land, parent, pioneer) if item is not None])
    ctx.count("lands_found")
    return LandResult(land, kind, pioneer, text)


async def _discovery_bonds(ctx: TickContext, search: LandSearch, land: EntityRow) -> None:
    bonds = BondRepository(ctx.session)
    if search.explorer is not None:
        await bonds.connect(BondDraft(search.explorer.id, land.id, BondKind.DISCOVERED, ctx.epoch, search.reason or "found unknown lands"))
    if search.leader is not None and (search.explorer is None or search.leader.id != search.explorer.id):
        led = f"led {search.explorer.name}'s expedition" if search.explorer else "led the expedition"
        await bonds.connect(BondDraft(search.leader.id, land.id, BondKind.DISCOVERED, ctx.epoch, led))
    if search.foreign_god is not None:
        await bonds.connect(BondDraft(search.foreign_god.id, land.id, BondKind.PRODUCED, ctx.epoch, "the foreign god who raised it"))


async def _maybe_pioneers(ctx: TickContext, search: LandSearch, land: EntityRow, rng: SeededRandom) -> EntityRow | None:
    explorer = search.explorer
    if not search.pioneers or explorer is None or explorer.status is not EntityStatus.CANON or explorer.entity_type not in LAND_COMMUNITIES:
        return None
    chance = min(PERCENT, ctx.rules.exploration.pioneer_chance * (2 if search.narrow else 1))
    return await pioneers(ctx, explorer, land) if rng.chance(chance) else None


def _land_text(search: LandSearch, land: EntityRow, parent: EntityRow | None, world: WorldRow, pioneer: EntityRow | None) -> str:
    kind_word = "place" if parent is not None else "region"
    if search.foreign_god is not None:
        inside = f" (inside {parent.name})" if parent is not None else ""
        return f"{search.foreign_god.name} raised a new {kind_word} on the world {world.name}: {land.name}{inside}."
    who = search.explorer.name if search.explorer is not None else "Someone"
    why = f", {search.reason}," if search.reason else ""
    found = f"{land.name} was found inside {parent.name}" if parent is not None else f"a new region, {land.name}, entered the map"
    elsewhere = f" (on the world {world.name})" if search.explorer is not None and search.explorer.world_id != world.id else ""
    settled = f"; its pioneers founded {pioneer.name} there" if pioneer is not None else ""
    return f"{who}{why} set out into unknown lands: {found}{elsewhere}{settled}."


async def pioneers(ctx: TickContext, explorer: EntityRow, land: EntityRow) -> EntityRow | None:
    limits, settings = ctx.rules.limits, ctx.rules.exploration
    population = stat(explorer, POPULATION_KEY)
    if population is None:
        return None
    floor = limits.people_population_floor if explorer.entity_type is EntityType.PEOPLE else limits.population_floor
    migrants = min(max(0, population - floor), limits.settlement_population_cap, round(population * settings.pioneer_share_pct / PERCENT))
    if migrants < max(settings.pioneer_min_population, limits.population_floor):
        return None
    put_stat(ctx.rules, explorer, POPULATION_KEY, population - migrants)
    derived = await Namer(ctx.session, ctx.rules).from_speaker(explorer.id, seed_of(explorer.id, land.id, "pioneers"), NameKind.PLACE)
    settlement = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=derived or f"{explorer.name} Pioneers",
            entity_type=EntityType.SETTLEMENT,
            body=f"{several(migrants, 'pioneer', 'pioneers')} from {explorer.name} settled the newly found lands of {land.name}.",
            stats=SettlementStats(
                population=migrants,
                prosperity=settings.pioneer_prosperity,
                defense=settings.pioneer_defense,
                piety=stat_or(explorer, PIETY_KEY, settings.pioneer_default_piety),
            ),
            power=max(1, explorer.power_level - 1),
            world_id=land.world_id,
            location_id=land.id,
            subtype="pioneer settlement",
            flags=(EntityFlag.PIONEER, EntityFlag.NAME_FROM_LANGUAGE) if derived else (EntityFlag.PIONEER,),
        ),
    )
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(explorer.id, settlement.id, BondKind.MIGRATED_TO, ctx.epoch, f"pioneers: {several(migrants, 'person', 'people')}"))
    await bonds.connect(BondDraft(settlement.id, explorer.id, BondKind.DESCENDS_FROM, ctx.epoch, "pioneers"))
    await bind_language_and_faith(ctx, settlement, source=explorer)
    return settlement


async def route_method(ctx: TickContext, entity: EntityRow, knowledge: KnowledgeMap | None = None) -> TravelMethod | None:
    known = (knowledge or await KnowledgeMap.load(ctx.session)).branches(entity.id)
    for branch, method in (
        (KnowledgeBranch.GATE_LORE, TravelMethod.ANCIENT_GATE),
        (KnowledgeBranch.PATHFINDING, TravelMethod.SPACE_FOLD),
        (KnowledgeBranch.SKY_NAVIGATION, TravelMethod.LIGHT_SAIL),
        (KnowledgeBranch.ASTRONOMY, TravelMethod.WORMHOLE),
    ):
        if branch in known:
            return method
    if await has_tamed_mount(ctx.session, entity.id):
        return TravelMethod.COSMIC_MOUNT
    return TravelMethod.DREAM_JOURNEY if KnowledgeBranch.MAGIC in known else None


class SearchStatus(StrEnum):
    ROUTE = "route"
    INTUITION = "intuition"
    NONE = "none"
    IGNORANT = "ignorant"


@dataclass(frozen=True)
class RouteSearch:
    status: SearchStatus
    method: TravelMethod | None = None
    route: RouteRow | None = None
    target: WorldRow | None = None
    vehicle: EntityRow | None = None
    text: str = ""


async def worlds_born_this_epoch(ctx: TickContext) -> int:
    born = int(await ctx.session.scalar(select(func.count()).select_from(WorldRow).where(WorldRow.created_epoch == ctx.epoch)) or 0)
    pending = int(
        await ctx.session.scalar(select(func.count()).select_from(HorizonIntuitionRow).where(HorizonIntuitionRow.status == HorizonStatus.PENDING)) or 0
    )
    return born + pending


async def can_birth_world(ctx: TickContext) -> bool:
    return await worlds_born_this_epoch(ctx) < ctx.rules.mortal_tools.unknown_world_per_epoch


async def _unconnected(ctx: TickContext, home: WorldRow) -> list[WorldRow]:
    statement = select(WorldRow).where(WorldRow.id != home.id, WorldRow.discovery.in_([Discovery.KNOWN, Discovery.LEGEND])).order_by(WorldRow.id)
    found: list[WorldRow] = []
    for world in await ctx.session.scalars(statement):
        linked = await ctx.session.scalar(
            select(RouteRow.id).where(
                RouteRow.active.is_(True),
                RouteRow.known.is_(True),
                ((RouteRow.world_a_id == home.id) & (RouteRow.world_b_id == world.id)) | ((RouteRow.world_a_id == world.id) & (RouteRow.world_b_id == home.id)),
            )
        )
        if linked is None:
            found.append(world)
    return found


async def _gate_vehicle(ctx: TickContext, me: EntityRow, target: WorldRow, how: str) -> EntityRow:
    tools = ctx.rules.mortal_tools
    rng = ctx.rng(seed_of("gate", me.id))
    location = me.id if me.entity_type is EntityType.SETTLEMENT else me.location_id
    gate = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{me.name} Gate",
            entity_type=EntityType.VESSEL,
            body=f"An ancient stone ring found by {me.name}, opening onto the world {target.name}. {how}",
            stats=VesselStats(
                speed=tools.gate_speed,
                range=tools.gate_range,
                crew=0,
                armor=tools.gate_armor,
                strangeness=clamp_percent(tools.gate_strangeness_base + rng.die(tools.gate_strangeness_die)),
            ),
            power=tools.gate_power,
            world_id=me.world_id,
            location_id=location,
            subtype="ancient gate",
        ),
    )
    await set_vessel_kind(ctx.session, gate.id, VehicleKind.GATE)
    return gate


async def search_route(ctx: TickContext, me: EntityRow, how: str, *, certain: bool = False) -> RouteSearch:
    method = await route_method(ctx, me) or (TravelMethod.DREAM_JOURNEY if certain else None)
    if method is None:
        return RouteSearch(SearchStatus.IGNORANT)
    home = await ctx.session.get(WorldRow, me.world_id)
    if home is None or home.discovery is Discovery.FORGOTTEN:
        return RouteSearch(SearchStatus.NONE, method)
    tools = ctx.rules.mortal_tools
    rng = ctx.rng(seed_of("route_search", me.id))
    unconnected = await _unconnected(ctx, home)
    roll = (
        float("inf")
        if certain
        else rng.die(PERCENT) + stat_or(me, INTELLECT_KEY, stat_or(me, INFLUENCE_KEY, tools.default_stat)) / tools.route_intellect_divisor
    )
    if unconnected and roll >= tools.route_threshold:
        target = rng.pick(unconnected)
        vehicle = await _gate_vehicle(ctx, me, target, how) if method is TravelMethod.ANCIENT_GATE else None
        route = await open_route(
            ctx.session,
            ctx.rules,
            rng,
            ctx.epoch,
            RouteSpec(home.id, target.id, method, controller_id=me.id, vehicle_id=vehicle.id if vehicle else None, description=how),
        )
        text = f"{me.name} found a route to the world {target.name}: {method.value.replace('_', ' ')} ({several(route.duration_epochs, 'epoch', 'epochs')})."
        return RouteSearch(SearchStatus.ROUTE, method, route, target, vehicle, text)
    if roll >= tools.unknown_world_threshold and await can_birth_world(ctx):
        return RouteSearch(SearchStatus.INTUITION, method)
    return RouteSearch(SearchStatus.NONE, method)


async def record_intuition(ctx: TickContext, me: EntityRow, how: str, method: TravelMethod | None) -> str:
    intuition = HorizonIntuitionRow(mortal_entity_id=me.id, world_id=me.world_id, epoch=ctx.epoch, how=how, method=method, status=HorizonStatus.PENDING)
    ctx.session.add(intuition)
    await ctx.session.flush()
    ctx.session.add(DeferredStepRow(epoch=ctx.epoch, kind=DeferredStepKind.SENSED_WORLD, requested_by_node_id=me.id, payload={"intuition_id": intuition.id}))
    await ctx.session.flush()
    ctx.count("intuitions")
    return f"{me.name}, searching {how}, sensed the existence of a world nobody knew; at the end of the epoch that world will come to light."


async def held_intuitions(session: AsyncSession) -> set[int]:
    steps = await session.scalars(
        select(DeferredStepRow).where(DeferredStepRow.kind == DeferredStepKind.SENSED_WORLD, DeferredStepRow.status == DeferredStepStatus.HELD)
    )
    return {int(step.payload["intuition_id"]) for step in steps if "intuition_id" in step.payload}


async def pending_intuitions(session: AsyncSession) -> list[HorizonIntuitionRow]:
    kept = await held_intuitions(session)
    rows = await session.scalars(select(HorizonIntuitionRow).where(HorizonIntuitionRow.status == HorizonStatus.PENDING).order_by(HorizonIntuitionRow.id))
    return [row for row in rows if row.id not in kept]


async def begin_intuition(session: AsyncSession, intuition: HorizonIntuitionRow) -> EntityRow | None:
    intuition.status = HorizonStatus.PROCESSING
    seeker = await session.get(EntityRow, intuition.mortal_entity_id)
    if seeker is None or seeker.status not in (EntityStatus.CANON, EntityStatus.FULFILLED):
        intuition.status = HorizonStatus.WASTED
        seeker = None
    await session.flush()
    return seeker


def intuition_inspiration(seeker: EntityRow, intuition: HorizonIntuitionRow) -> str:
    return f"{seeker.name} mortals, searching {intuition.how or 'the sky'}, found the way to a world nobody knew."


async def settle_intuition(ctx: TickContext, intuition: HorizonIntuitionRow, born: WorldRow | None) -> str | None:
    seeker = await ctx.session.get(EntityRow, intuition.mortal_entity_id)
    if born is None or seeker is None:
        intuition.status = HorizonStatus.WASTED
        await ctx.session.flush()
        return None
    intuition.status = HorizonStatus.BORN
    intuition.result_world_id = born.id
    try:
        await open_route(
            ctx.session,
            ctx.rules,
            ctx.rng(seed_of("intuition", intuition.id)),
            ctx.epoch,
            RouteSpec(seeker.world_id, born.id, intuition.method or TravelMethod.DREAM_JOURNEY, controller_id=seeker.id, description=intuition.how),
        )
        tail = ""
    except ValidationFailedError:
        await WorldRepository(ctx.session).set_discovery(born, Discovery.LEGEND)
        tail = " But its route closed; the world is remembered only as a legend."
    text = f"{seeker.name} discovered a world nobody knew: {born.name}.{tail}"
    await ctx.chronicle(
        ChronicleKind.EXPLORATION,
        text,
        template_key="exploration.sensed_world_born",
        entity_ids=[seeker.id],
        world_id=born.id,
        feed_category=FeedCategory.WORLD,
    )
    return text


async def recover_intuitions(session: AsyncSession) -> int:
    rows = list(await session.scalars(select(HorizonIntuitionRow).where(HorizonIntuitionRow.status == HorizonStatus.PROCESSING)))
    for row in rows:
        row.status = HorizonStatus.PENDING
    await session.flush()
    return len(rows)


def _may_explore(rules: Rules, entity: EntityRow) -> bool:
    return entity.entity_type is EntityType.MORTAL or unlocked(rules, entity.civ_tier or 0, TierCapability.EXPLORATION)


async def planet_exploration(ctx: TickContext, world_id: int | None = None) -> list[LandResult]:
    settings = ctx.rules.exploration
    if settings.per_epoch_cap <= 0:
        return []
    found: list[LandResult] = []
    scene = await ExplorationScene.load(ctx)
    rng = ctx.rng("planet")
    for world in await WorldRepository(ctx.session).reachable_worlds():
        if world_id is not None and world.id != world_id:
            continue
        found.extend(await _explore_world(ctx, scene, world, rng))
    return found


async def _explore_world(ctx: TickContext, scene: ExplorationScene, world: WorldRow, rng: SeededRandom) -> list[LandResult]:
    settings = ctx.rules.exploration
    measure = await land_measure(ctx.session, ctx.rules, world.id, scene.atlas)
    communities = await canon(ctx.session, LAND_COMMUNITIES, world.id)
    entities = [entity for entity in await canon(ctx.session, SEEKER_TYPES, world.id) if _may_explore(ctx.rules, entity)]
    candidates = [
        entity for entity in entities if (entity.entity_type in COMMUNITY_TYPES and headcount(entity) >= settings.min_population) or await explores(ctx, entity)
    ]
    pressures = [(await exploration_pressure(ctx, scene, entity, communities), entity) for entity in candidates]
    pressures.sort(key=lambda item: (-item[0].pct, item[1].id))
    found: list[LandResult] = []
    for measured, entity in pressures:
        if len(found) >= settings.per_epoch_cap:
            break
        if (entity.entity_type is EntityType.MORTAL and entity.id in scene.away) or held(entity.id):
            continue
        stale = measured.explorer is not None and measured.explorer.id in scene.away
        pressure = await exploration_pressure(ctx, scene, entity, communities) if stale else measured
        if not rng.chance(pressure.pct):
            continue
        reason = exploration_sentence(pressure.reasons, rng.below(len(PHRASES[Reason.NARROW])), pressure.explorer.name if pressure.explorer else None)
        result = await find_land(
            ctx,
            LandSearch(
                world.id, explorer=entity, leader=pressure.explorer, reason=reason, narrow=measure.narrow, kind=None if measure.regions else EntityType.REGION
            ),
        )
        if result is not None:
            found.append(result)
            scene.away.add(entity.id)
            if pressure.explorer is not None:
                scene.away.add(pressure.explorer.id)
    return found


async def cosmic_exploration(ctx: TickContext) -> int:
    settings = ctx.rules.exploration
    if settings.route_search_cap <= 0:
        return 0
    knowledge = await KnowledgeMap.load(ctx.session)
    rng = ctx.rng("cosmic")
    seekers = [
        entity
        for entity in await canon(ctx.session, SEEKER_TYPES)
        if (entity.entity_type is EntityType.MORTAL or unlocked(ctx.rules, entity.civ_tier or 0, TierCapability.ROUTE_SEARCH))
        and await route_method(ctx, entity, knowledge) is not None
    ]
    searched = 0
    for seeker in unheld(rng.shuffled(seekers)):
        if searched >= settings.route_search_cap:
            break
        if not rng.chance(settings.route_search_chance * (1 - await hidden_sky(ctx.session, ctx.rules, seeker.world_id))):
            continue
        searched += 1
        await report_search(ctx, seeker, await search_route(ctx, seeker, COSMIC_SEARCH_HOW), COSMIC_SEARCH_HOW)
    return searched


async def report_search(ctx: TickContext, seeker: EntityRow, result: RouteSearch, how: str) -> str:
    if result.status is SearchStatus.ROUTE:
        text = result.text
    elif result.status is SearchStatus.INTUITION:
        text = await record_intuition(ctx, seeker, how, result.method)
    elif result.status is SearchStatus.IGNORANT:
        text = f"{seeker.name} knows no way between worlds to search for."
    else:
        text = f"{seeker.name} searched for the road to other worlds but did not find it this epoch."
    await note(ctx, text, key=f"exploration.route_search.{result.status.value}", ids=[seeker.id], feed=FeedCategory.VOYAGE)
    return text


async def foreign_god_land(ctx: TickContext, god_id: int | None = None) -> list[LandResult]:
    statement = select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id)
    rng = ctx.rng("foreign_land")
    raised: list[LandResult] = []
    for god in await ctx.session.scalars(statement):
        if god_id is not None and god.id != god_id:
            continue
        if god_id is None and (held(god.id, god.world_id) or not rng.chance(ctx.rules.exploration.foreign_god_raise_land_chance)):
            continue
        has_regions = bool(await canon(ctx.session, [EntityType.REGION], god.world_id))
        result = await find_land(ctx, LandSearch(god.world_id, foreign_god=god, kind=None if has_regions else EntityType.REGION, pioneers=False))
        if result is not None:
            raised.append(result)
    return raised


@reads(
    "cult.followers",
    "mortal.agility",
    "mortal.intellect",
    "people.piety",
    "people.population",
    "people.prosperity",
    "place.fertility",
    "region.breadth",
    "region.fertility",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.bodies",
    "table.bonds",
    "table.community_societies",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.horizon_intuitions",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.nodes",
    "table.place_environment",
    "table.routes",
    "table.vessel_profiles",
    "table.world_maps",
)
@writes(
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.deferred_steps",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.horizon_intuitions",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.name_registry",
    "table.routes",
    "table.vessel_profiles",
)
async def exploration_phase(ctx: TickContext) -> None:
    await planet_exploration(ctx)
    await cosmic_exploration(ctx)
    await foreign_god_land(ctx)


@dataclass(frozen=True)
class Discovered:
    land: EntityRow
    discoverer: EntityRow | None


@dataclass(frozen=True)
class WorldHorizon:
    world: WorldRow
    measure: LandMeasure
    discoveries: list[Discovered]


@dataclass(frozen=True)
class ExplorationSummary:
    worlds: list[WorldHorizon]
    chronicle: list[ChronicleRow]
    intuitions: list[HorizonIntuitionRow]
    lands_cap: int
    base_chance: int
    route_search_chance: int
    narrow_threshold: int


async def exploration_summary(session: AsyncSession, rules: Rules) -> ExplorationSummary:
    atlas = await RegionAtlas.load(session)
    discovered = await flags_by_entity(session, EntityFlag.DISCOVERY)
    worlds: list[WorldHorizon] = []
    for world in await WorldRepository(session).reachable_worlds():
        lands = [land for land in await canon(session, [EntityType.REGION, EntityType.PLACE], world.id) if land.id in discovered]
        recent = sorted(lands, key=lambda land: -land.id)[: rules.exploration.summary_list]
        items = []
        for land in recent:
            finder = await session.scalar(
                select(BondRow.source_node_id)
                .where(BondRow.target_node_id == land.id, BondRow.kind == BondKind.DISCOVERED, BondRow.state == BondState.ACTIVE)
                .limit(1)
            )
            items.append(Discovered(land, await session.get(EntityRow, finder) if finder is not None else None))
        worlds.append(WorldHorizon(world, await land_measure(session, rules, world.id, atlas), items))
    chronicle = list(
        await session.scalars(
            select(ChronicleRow).where(ChronicleRow.kind == ChronicleKind.EXPLORATION).order_by(ChronicleRow.id.desc()).limit(SUMMARY_CHRONICLE_LINES)
        )
    )
    intuitions = list(await session.scalars(select(HorizonIntuitionRow).order_by(HorizonIntuitionRow.id.desc()).limit(SUMMARY_INTUITION_LINES)))
    settings = rules.exploration
    return ExplorationSummary(
        worlds, chronicle, intuitions, settings.per_epoch_cap, settings.base_chance, settings.route_search_chance, settings.crowded_communities_per_region
    )


async def _living(session: AsyncSession, entity_id: int) -> EntityRow:
    entity = await session.get(EntityRow, entity_id)
    if entity is None or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such living record.")
    return entity


async def send_to_explore(session: AsyncSession, rules: Rules, entity_id: int, kind: EntityType | None = None) -> LandResult | None:
    if kind is not None and kind not in (EntityType.REGION, EntityType.PLACE):
        raise ValidationFailedError("Explorers find regions or places.")
    ctx = await manual_context(session, "explore", rules, key=str(entity_id))
    entity = await _living(session, entity_id)
    measure = await land_measure(session, rules, entity.world_id)
    return await find_land(
        ctx,
        LandSearch(
            entity.world_id, explorer=entity, reason="sent by the creator's hand", narrow=measure.narrow, kind=kind if measure.regions else EntityType.REGION
        ),
    )


async def exploration_round(session: AsyncSession, rules: Rules, world_id: int) -> list[LandResult]:
    return await planet_exploration(await manual_context(session, "exploration_round", rules, key=str(world_id)), world_id)


async def order_foreign_god_land(session: AsyncSession, rules: Rules, god_id: int) -> list[LandResult]:
    return await foreign_god_land(await manual_context(session, "foreign_land", rules, key=str(god_id)), god_id)


async def run_exploration_phase(session: AsyncSession, rules: Rules) -> None:
    await exploration_phase(await manual_context(session, "exploration", rules))


PHASES = (Phase("exploration", exploration_phase),)
