from collections import deque
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civilization import unlocked
from aerona.catalog.travel import TRAVEL_METHODS
from aerona.catalog.worlds import HARSH_ATMOSPHERES
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherEffect
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import JourneyEventKind, JourneyIntent, JourneyStatus, RouteClosure, RouteState, TravelMethod
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import KnowledgeStats, LegendStats, SettlementStats
from aerona.engine.body.book import factor
from aerona.engine.context import TickContext
from aerona.engine.cosmos.discovery import mark_world_discovered
from aerona.engine.cosmos.fauna import stowaway
from aerona.engine.cosmos.pilgrimage import has_holy_site, reach_holy_site
from aerona.engine.cosmos.routes import (
    LIVE_JOURNEYS,
    JourneySpec,
    RouteBook,
    add_event,
    can_use_route,
    connect_world,
    method_label,
    other_end,
    reveal_hidden_route,
    sever_route,
    start_journey,
    stitch_route,
    touches,
    world_name,
)
from aerona.engine.ecology.beasts import mount_of
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.book import pressures_of
from aerona.engine.mind.drives import expedition_drive
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.culture_exchange import cultural_contact
from aerona.engine.phases.exploration import LandSearch, find_land
from aerona.engine.phases.sky import time_difference
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.knowledge import KnowledgeMap, knows
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import scaled_cap
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import active_bonds, canon, connect, count_communities, spoken_language
from aerona.engine.primitives.records import RecordSpec, open_record, retire
from aerona.engine.primitives.stats import headcount, put_stat, shift_bounded, stat, stat_or
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import declare_war
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

M = TravelMethod
REVEAL_BRANCH: dict[TravelMethod, KnowledgeBranch] = {
    M.ANCIENT_GATE: KnowledgeBranch.GATE_LORE,
    M.LIGHT_SAIL: KnowledgeBranch.SKY_NAVIGATION,
    M.SLINGSHOT_ORBIT: KnowledgeBranch.SKY_NAVIGATION,
    M.SPACE_FOLD: KnowledgeBranch.PATHFINDING,
    M.DREAM_JOURNEY: KnowledgeBranch.MAGIC,
    M.WORMHOLE: KnowledgeBranch.ASTRONOMY,
}
ROAD_EVENT_TEXT: dict[JourneyEventKind, str] = {
    JourneyEventKind.PIRATES: "void pirates attacked",
    JourneyEventKind.VOID_STORM: "they were caught in a void storm",
    JourneyEventKind.CREATURE: "they met a cosmic creature",
    JourneyEventKind.LOST_WAY: "they lost their way and turned back",
    JourneyEventKind.SWALLOWED: "some were digested inside the creature",
    JourneyEventKind.DREAM_NOT_RETURNED: "those left in the dream did not wake",
    JourneyEventKind.MEMORY_LOSS: "the river's water took their memories",
}
ARMOUR_EVENTS = frozenset({JourneyEventKind.PIRATES, JourneyEventKind.CREATURE, JourneyEventKind.VOID_STORM})
SPECIAL_EVENTS = frozenset({JourneyEventKind.SWALLOWED, JourneyEventKind.DREAM_NOT_RETURNED, JourneyEventKind.MEMORY_LOSS})
SWALLOWED_TEXT: dict[JourneyEventKind, str] = {
    JourneyEventKind.LOST_WAY: "they lost their bearings in the void",
    JourneyEventKind.SWALLOWED: "the creature carrying them never let them go",
    JourneyEventKind.DREAM_NOT_RETURNED: "no one woke from the dream",
    JourneyEventKind.MEMORY_LOSS: "the river took every memory; forgetting who they were, they melted into its water",
    JourneyEventKind.PIRATES: "void pirates left no one alive",
    JourneyEventKind.VOID_STORM: "a void storm swallowed them",
    JourneyEventKind.CREATURE: "a cosmic creature swallowed the caravan",
}
COMMON_EVENTS = (JourneyEventKind.PIRATES, JourneyEventKind.VOID_STORM, JourneyEventKind.CREATURE, JourneyEventKind.LOST_WAY)
METHOD_EVENTS = {M.SWALLOWED: JourneyEventKind.SWALLOWED, M.DREAM_JOURNEY: JourneyEventKind.DREAM_NOT_RETURNED, M.RIVER_OF_DEAD: JourneyEventKind.MEMORY_LOSS}
INTENT_SENT = {
    JourneyIntent.COLONY: "a colony caravan",
    JourneyIntent.EXPLORATION: "an exploration expedition",
    JourneyIntent.TRADE: "a trade expedition",
    JourneyIntent.CONQUEST: "a conquest fleet",
    JourneyIntent.PILGRIMAGE: "pilgrims",
}
LAND_COMMUNITIES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
FERTILITY_KEY = "fertility"
PROSPERITY_KEY = "prosperity"
PIETY_KEY = "piety"
CHARISMA_KEY = "charisma"
ARMOR_KEY = "armor"
INTELLECT_KEY = "intellect"
POPULATION_KEY = "population"


async def hidden_routes(ctx: TickContext) -> int:
    session, travel = ctx.session, ctx.rules.travel
    for world in await WorldRepository(session).reachable_worlds():
        await connect_world(ctx, world)
    book = await RouteBook.load(session, ctx.rules, ctx.epoch)
    rng = ctx.rng("hidden")
    knowledge = await KnowledgeMap.load(session)
    sons = [son for son in await session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id))]
    revealed = 0
    for route in book.routes:
        if route.known or (not route.active and route.temp_closed_until_epoch is None):
            continue
        if route.world_a_id in book.forgotten or route.world_b_id in book.forgotten:
            continue
        ends = (route.world_a_id, route.world_b_id)
        branch = REVEAL_BRANCH.get(route.method)
        communities = [item for world in ends for item in await canon(session, COMMUNITY_TYPES, world)]
        knower = next((item for item in communities if branch is not None and knowledge.knows(item.id, branch)), None)
        mortals = [
            item
            for world in ends
            for item in await canon(session, [EntityType.MORTAL], world)
            if stat_or(item, INTELLECT_KEY, 0) * await factor(session, item.id, Capacity.SCHOLARSHIP) >= travel.sensing_min_intellect
        ]
        sage = max(mortals, key=lambda item: (stat_or(item, INTELLECT_KEY, 0), -item.id)) if mortals else None
        son = next((item for item in sons if item.current_world_id in ends), None)
        chance = (
            (travel.hidden_knower_chance if knower else travel.hidden_base_chance)
            + (travel.hidden_sensing_mortal_bonus_pct if sage else 0)
            + (travel.hidden_son_bonus_pct if son else 0)
        )
        if not rng.chance(chance):
            continue
        route.known = True
        revealed += 1
        await _announce_hidden(ctx, route, knower is not None, sage, son, severed=not route.active)
    return revealed


async def _announce_hidden(ctx: TickContext, route: RouteRow, knower: bool, sage: EntityRow | None, son: SonRow | None, *, severed: bool) -> None:
    first, second = await world_name(ctx.session, route.world_a_id), await world_name(ctx.session, route.world_b_id)
    credit = ""
    if not knower and sage is not None:
        credit = f" {sage.name} sensed it in a dream."
    elif not knower and son is not None:
        credit = f" {son.name} heard the passage tremble."
    tail = " The route is severed for now; it will open when its stitch closes." if severed else ""
    await note(
        ctx,
        f"A hidden route was revealed between {first} and {second}: {method_label(route.method)}.{credit}{tail}",
        key="travel.hidden_revealed",
        ids=[sage.id] if sage and not knower else [],
    )
    for world_id in (route.world_a_id, route.world_b_id):
        world = await ctx.session.get(WorldRow, world_id)
        if world is not None:
            await mark_world_discovered(ctx, world, f"the hidden route to it ({method_label(route.method)}) was revealed")


async def _road_knowledge(ctx: TickContext, community: EntityRow, route: RouteRow, branch: KnowledgeBranch) -> EntityRow:
    existing = [item for item in await canon(ctx.session, [EntityType.KNOWLEDGE], community.world_id) if item.knowledge_branch is branch]
    if existing:
        return existing[0]
    travel = ctx.rules.travel
    label = method_label(route.method)
    first, second = await world_name(ctx.session, route.world_a_id), await world_name(ctx.session, route.world_b_id)
    return await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{community.name} {label} Knowledge",
            entity_type=EntityType.KNOWLEDGE,
            body=f"{community.name} solved the secret of {label} while trying to understand the route between {first} and {second}.",
            stats=KnowledgeStats(level=1, spread=travel.route_knowledge_spread),
            power=travel.route_knowledge_power,
            world_id=community.world_id,
            location_id=community.location_id,
            subtype="road knowledge",
            knowledge_branch=branch,
        ),
    )


async def teach_route(ctx: TickContext, community: EntityRow, route: RouteRow) -> EntityRow | None:
    branch = TRAVEL_METHODS[route.method].required_branch
    if branch is None or await knows(ctx.session, community.id, branch):
        return None
    knowledge = await _road_knowledge(ctx, community, route, branch)
    await connect(ctx.session, community.id, knowledge.id, BondKind.KNOWS, ctx.epoch, description="learned while trying to understand the route")
    other = await world_name(ctx.session, other_end(route, community.world_id)) if touches(route, community.world_id) else "other worlds"
    await note(
        ctx,
        f"{community.name} learned the secret of {method_label(route.method)}; the road to {other} is now open to them.",
        key="travel.route_knowledge",
        ids=[community.id, knowledge.id],
    )
    return knowledge


async def route_knowledge(ctx: TickContext) -> int:
    travel = ctx.rules.travel
    book = await RouteBook.load(ctx.session, ctx.rules, ctx.epoch)
    knowledge = await KnowledgeMap.load(ctx.session)
    rng = ctx.rng("route_knowledge")
    learned = 0
    for route in [item for item in book.routes if item.active and item.known]:
        if learned >= travel.route_knowledge_cap:
            break
        branch = TRAVEL_METHODS[route.method].required_branch
        if branch is None:
            continue
        for world_id in (route.world_a_id, route.world_b_id):
            candidates = [item for item in await canon(ctx.session, COMMUNITY_TYPES, world_id) if not knowledge.knows(item.id, branch)]
            if not candidates:
                continue
            community = max(candidates, key=lambda item: (stat_or(item, "craft", 0) + stat_or(item, "magic", 0), -item.id))
            if not rng.chance(travel.route_knowledge_chance):
                continue
            if await teach_route(ctx, community, route) is not None:
                learned += 1
                break
    return learned


def expedition_pressure(rules: Rules, community: EntityRow, fertility: int) -> int:
    travel = rules.travel
    pressure = travel.expedition_barren_pct if fertility < travel.expedition_barren_threshold else 0
    pressure += travel.expedition_crowd_pct if headcount(community) > travel.expedition_crowd_threshold else 0
    pressure += travel.expedition_poverty_pct if stat_or(community, PROSPERITY_KEY, travel.default_prosperity) < travel.expedition_poverty_threshold else 0
    return travel.expedition_base_pct + pressure


async def _visits(session: AsyncSession, world_id: int) -> int:
    return int(await session.scalar(select(func.count()).select_from(JourneyRow).where(JourneyRow.destination_world_id == world_id)) or 0)


async def _world_population(session: AsyncSession, world_id: int) -> int:
    return sum(headcount(item) for item in await canon(session, LAND_COMMUNITIES, world_id))


async def weighted_route(ctx: TickContext, routes: list[RouteRow], home: int, rng: SeededRandom) -> RouteRow | None:
    if len(routes) <= 1:
        return routes[0] if routes else None
    travel = ctx.rules.travel
    weights = []
    for route in routes:
        target = other_end(route, home)
        weight = PERCENT / (1 + await _visits(ctx.session, target) * travel.expedition_visit_weight_pct / PERCENT)
        weights.append(weight * (1 if await _world_population(ctx.session, target) > 0 else travel.expedition_empty_world_weight_pct / PERCENT))
    return rng.weighted(routes, weights)


async def _fertility_of(session: AsyncSession, rules: Rules, community: EntityRow) -> int:
    location = await session.get(EntityRow, community.location_id) if community.location_id is not None else None
    return stat_or(location, FERTILITY_KEY, rules.travel.default_fertility) if location is not None else rules.travel.default_fertility


async def _travelling(session: AsyncSession) -> set[int]:
    return set(await session.scalars(select(JourneyRow.traveller_entity_id).where(JourneyRow.status.in_(list(LIVE_JOURNEYS)))))


def choose_intent(rules: Rules, rng: SeededRandom, tier: int, target_empty: bool, *, holy_site: bool = False, warlike: bool = False) -> JourneyIntent:
    travel = rules.travel
    if not target_empty and holy_site and rng.chance(travel.pilgrimage_intent_chance):
        return JourneyIntent.PILGRIMAGE
    if not target_empty and warlike and rng.chance(travel.conquest_intent_chance):
        return JourneyIntent.CONQUEST
    colony_allowed = unlocked(rules, tier, TierCapability.COLONY)
    if colony_allowed and (target_empty or rng.chance(travel.colony_intent_chance)):
        return JourneyIntent.COLONY
    return JourneyIntent.EXPLORATION if rng.chance(travel.exploration_intent_chance) else JourneyIntent.TRADE


async def spontaneous_expeditions(ctx: TickContext) -> int:
    travel = ctx.rules.travel
    book = await RouteBook.load(ctx.session, ctx.rules, ctx.epoch)
    if not book.open_known() or travel.expedition_cap <= 0:
        return 0
    rng = ctx.rng("expeditions")
    away = await _travelling(ctx.session)
    candidates = []
    for community in await canon(ctx.session, LAND_COMMUNITIES):
        if headcount(community) < travel.expedition_min_population or community.id in away:
            continue
        if not unlocked(ctx.rules, community.civ_tier or 0, TierCapability.EXPEDITION):
            continue
        if await pressures_of(ctx.session, community.id):
            chance = round(travel.expedition_base_pct * await expedition_drive(ctx.session, ctx.rules, community.id))
        else:
            chance = expedition_pressure(ctx.rules, community, await _fertility_of(ctx.session, ctx.rules, community))
        candidates.append((chance * rng.random(), chance, community))
    candidates.sort(key=lambda item: (-item[0], item[2].id))
    sent = 0
    cap = scaled_cap(travel.expedition_cap, travel.expedition_cap_community_divisor, await count_communities(ctx.session))
    for _weight, chance, community in candidates:
        if sent >= cap:
            break
        if await _send_spontaneously(ctx, book, community, chance, rng):
            sent += 1
    return sent


async def _send_spontaneously(ctx: TickContext, book: RouteBook, community: EntityRow, chance: int, rng: SeededRandom) -> bool:
    usable = [
        route for route in book.open_known(community.world_id) if await can_use_route(ctx.session, ctx.rules, ctx.epoch, community, route, book=book) is None
    ]
    route = await weighted_route(ctx, usable, community.world_id, rng)
    if route is None or not rng.chance(chance):
        return False
    target = other_end(route, community.world_id)
    warlike = max(stat_or(community, "martiality", 0), stat_or(community, "defense", 0)) >= ctx.rules.travel.conquest_min_martiality
    empty = await _world_population(ctx.session, target) == 0
    intent = choose_intent(ctx.rules, rng, community.civ_tier or 0, empty, holy_site=await has_holy_site(ctx.session, community, target), warlike=warlike)
    settling = intent in (JourneyIntent.COLONY, JourneyIntent.CONQUEST)
    carried = round(headcount(community) * ctx.rules.travel.colony_share_pct / PERCENT) if settling else 0
    try:
        await start_journey(ctx, JourneySpec(community, route, intent, carried))
    except ValidationFailedError:
        return False
    text = f"{community.name} sent {INTENT_SENT[intent]} to {await world_name(ctx.session, target)} by way of {method_label(route.method)}."
    await note(ctx, text, key="travel.expedition_sent", ids=[community.id])
    return True


async def bridge_collapse(ctx: TickContext) -> int:
    statement = (
        select(RouteRow).where(RouteRow.method == M.DIVINE_BRIDGE, RouteRow.active.is_(True), RouteRow.builder_son_id.is_not(None)).order_by(RouteRow.id)
    )
    collapsed = 0
    for route in list(await ctx.session.scalars(statement)):
        builder = await ctx.session.get(SonRow, route.builder_son_id) if route.builder_son_id is not None else None
        if builder is not None and builder.status is SonStatus.ACTIVE:
            continue
        route.active = False
        route.closure = RouteClosure.COLLAPSED
        state = "died" if builder is None or builder.status is SonStatus.DEAD else "fell asleep"
        rng = ctx.rng(f"bridge_collapse.{route.id}")
        for journey in await ctx.session.scalars(select(JourneyRow).where(JourneyRow.route_id == route.id, JourneyRow.status.in_(LIVE_JOURNEYS))):
            fell = rng.chance(ctx.rules.travel_methods.bridge_collapse_loss_pct)
            add_event(
                journey, ctx.epoch, JourneyEventKind.BRIDGE_COLLAPSED, "the bridge fell from under them" if fell else "the bridge fell and they turned back"
            )
            journey.status = JourneyStatus.LOST if fell else JourneyStatus.RECALLED
            journey.end_epoch = ctx.epoch
        vehicle = await ctx.session.get(EntityRow, route.vehicle_entity_id) if route.vehicle_entity_id is not None else None
        if vehicle is not None and vehicle.status is EntityStatus.CANON:
            await retire(ctx.session, vehicle, ctx.epoch, f"Epoch {ctx.epoch}: collapsed when its builder {builder.name if builder else 'a god'} {state}.")
        first, second = await world_name(ctx.session, route.world_a_id), await world_name(ctx.session, route.world_b_id)
        await note(
            ctx,
            f"{builder.name if builder else 'A god'}'s divine bridge between {first} and {second} collapsed because its builder {state}.",
            key="travel.bridge_collapsed",
        )
        collapsed += 1
    return collapsed


def road_risk(rules: Rules, route: RouteRow, branches: set[KnowledgeBranch], vehicle: EntityRow | None, world_danger: int = 0, *, wind: int = 0) -> float:
    travel = rules.travel
    risk = route.danger / PERCENT + world_danger / PERCENT * travel.world_danger_risk_pct / PERCENT + wind / PERCENT * travel.wind_risk_pct / PERCENT
    if KnowledgeBranch.SKY_NAVIGATION in branches:
        risk *= travel.sky_navigation_risk_pct / PERCENT
    if KnowledgeBranch.VOID_LIVING in branches:
        risk *= travel.void_life_risk_pct / PERCENT
    if vehicle is not None:
        risk *= 1 - stat_or(vehicle, ARMOR_KEY, travel.default_vessel_armor) / travel.armor_risk_divisor
    return max(0.0, risk)


@dataclass
class JourneyScene:
    book: RouteBook
    knowledge: KnowledgeMap
    rng: SeededRandom
    ground: EnvironmentBook
    arrivals: list[int] = field(default_factory=list)

    def departure_wind(self, ctx: TickContext, journey: JourneyRow, traveller: EntityRow) -> int:
        region = self.ground.region_of(traveller.id)
        if region is None:
            return 0
        season = self.ground.season_at(region.world_id, journey.id)
        return self.ground.weather(ctx.environment.world_seed, ctx.epoch, region, season, f"journey.{journey.id}").effect(WeatherEffect.WIND)


async def _ghost_ship(ctx: TickContext, journey: JourneyRow, traveller: EntityRow, vehicle: EntityRow) -> EntityRow:
    travel = ctx.rules.travel
    await retire(ctx.session, vehicle, ctx.epoch, f"Epoch {ctx.epoch}: lost in the void.")
    legend = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{vehicle.name} Ghost",
            entity_type=EntityType.LEGEND,
            body=f"{vehicle.name} vanished in the void with {traveller.name}'s travellers; on some nights its lights are still seen.",
            stats=LegendStats(spread=travel.ghost_ship_legend_spread),
            power=travel.ghost_ship_legend_power,
            world_id=journey.origin_world_id,
            subtype="ghost ship",
        ),
    )
    await connect(ctx.session, legend.id, vehicle.id, BondKind.TELLS_OF, ctx.epoch, description="the ghost ship")
    return legend


def swallow_chance(rules: Rules, kind: JourneyEventKind, vehicle: EntityRow | None) -> float:
    travel = rules.travel
    if kind is JourneyEventKind.LOST_WAY:
        return float(travel.lost_chance)
    if kind in SPECIAL_EVENTS:
        return float(travel.special_loss_chance)
    armour = 1 - stat_or(vehicle, ARMOR_KEY, travel.default_vessel_armor) / travel.armor_risk_divisor if vehicle is not None else 1.0
    return travel.raid_loss_chance * max(0.0, armour)


async def _lost_caravan(ctx: TickContext, journey: JourneyRow, traveller: EntityRow, target: str, how: str) -> EntityRow:
    travel = ctx.rules.travel
    legend = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{traveller.name} Lost Caravan",
            entity_type=EntityType.LEGEND,
            body=f"{journey.population} travellers of {traveller.name} set out for {target}; {how}. Their names are spoken at home every year.",
            stats=LegendStats(spread=travel.lost_caravan_legend_spread),
            power=travel.lost_caravan_legend_power,
            world_id=journey.origin_world_id,
            subtype="lost caravan",
        ),
    )
    await connect(ctx.session, legend.id, traveller.id, BondKind.TELLS_OF, ctx.epoch, description="the lost caravan")
    return legend


async def road_event(ctx: TickContext, scene: JourneyScene, journey: JourneyRow, traveller: EntityRow, route: RouteRow) -> bool:
    travel = ctx.rules.travel
    vehicle = await ctx.session.get(EntityRow, journey.vehicle_entity_id) if journey.vehicle_entity_id is not None else None
    destination = await ctx.session.get(WorldRow, journey.destination_world_id)
    danger = destination.danger if destination is not None else 0
    wind = scene.departure_wind(ctx, journey, traveller)
    if not scene.rng.probability(road_risk(ctx.rules, route, scene.knowledge.branches(traveller.id), vehicle, danger, wind=wind)):
        return True
    kind = METHOD_EVENTS.get(route.method) or scene.rng.pick(COMMON_EVENTS)
    target = await world_name(ctx.session, journey.destination_world_id)
    if scene.rng.chance(swallow_chance(ctx.rules, kind, vehicle)):
        how = SWALLOWED_TEXT[kind]
        add_event(journey, ctx.epoch, kind, how, loss=journey.population)
        journey.status = JourneyStatus.LOST
        journey.end_epoch = ctx.epoch
        ghost = await _ghost_ship(ctx, journey, traveller, vehicle) if vehicle is not None and vehicle.status is EntityStatus.CANON else None
        caravan = await _lost_caravan(ctx, journey, traveller, target, how) if ghost is None and journey.population > 0 else None
        suffix = f"; {vehicle.name} is now a ghost-ship legend" if ghost is not None and vehicle is not None else ""
        travellers = f" ({journey.population} travellers)" if journey.population else ""
        await note(
            ctx,
            f"{traveller.name}'s expedition to {target} was lost on the road: {how}{travellers}{suffix}.",
            key="travel.vanished",
            ids=[traveller.id, *([ghost.id] if ghost is not None else []), *([caravan.id] if caravan is not None else [])],
            feed=None,
        )
        return False
    lost = round(journey.population * (travel.road_loss_base_pct / PERCENT + scene.rng.random() * travel.road_loss_random_pct / PERCENT))
    journey.population = max(0, journey.population - lost)
    add_event(journey, ctx.epoch, kind, ROAD_EVENT_TEXT[kind], loss=lost)
    if kind is JourneyEventKind.MEMORY_LOSS:
        journey.memory_lost = True
    if vehicle is not None and kind in ARMOUR_EVENTS:
        put_stat(ctx.rules, vehicle, ARMOR_KEY, stat_or(vehicle, ARMOR_KEY, travel.default_vessel_armor) - travel.vessel_armor_loss)
    tail = f"; {lost} people were lost" if lost else ""
    await note(ctx, f"On {traveller.name}'s journey to {target} {ROAD_EVENT_TEXT[kind]}{tail}.", key=f"travel.road.{kind.value}", ids=[traveller.id])
    return True


async def _closed_route(ctx: TickContext, journey: JourneyRow, traveller: EntityRow, route: RouteRow, scene: JourneyScene) -> None:
    status = scene.book.status(route)
    target = await world_name(ctx.session, journey.destination_world_id)
    if status.state is RouteState.SEVERED:
        if journey.status is not JourneyStatus.WAITING:
            journey.status = JourneyStatus.WAITING
            add_event(
                journey,
                ctx.epoch,
                JourneyEventKind.VOID_STORM,
                f"the route snapped; the expedition is waiting for the stitch to close (Epoch {status.opens_epoch})",
            )
            resume = f"it will continue when the stitch closes at the start of Epoch {status.opens_epoch}"
            text = f"{traveller.name}'s expedition to {target} waits at the mouth of the broken road; {resume}."
            await note(ctx, text, key="travel.waiting", ids=[traveller.id])
        return
    reason = {
        RouteState.FORGOTTEN: "the world at the end of the route was forgotten",
        RouteState.COLLAPSED: "the divine bridge collapsed",
        RouteState.SEALED: "the route was sealed",
    }.get(status.state, "the route collapsed")
    add_event(journey, ctx.epoch, JourneyEventKind.OTHER, f"{reason}; travellers were left in the void")
    journey.status = JourneyStatus.LOST
    journey.end_epoch = ctx.epoch
    await note(ctx, f"{traveller.name}'s journey to {target} vanished in the void: {reason}.", key="travel.journey_vanished", ids=[traveller.id])


async def advance_journey(ctx: TickContext, scene: JourneyScene, journey: JourneyRow) -> None:
    traveller = await ctx.session.get(EntityRow, journey.traveller_entity_id)
    route = await ctx.session.get(RouteRow, journey.route_id)
    if traveller is None or route is None:
        journey.status = JourneyStatus.LOST
        journey.end_epoch = ctx.epoch
        return
    if not route.active or scene.book.status(route).state is RouteState.FORGOTTEN:
        await _closed_route(ctx, journey, traveller, route, scene)
        return
    journey.status = JourneyStatus.UNDERWAY
    if not await road_event(ctx, scene, journey, traveller, route):
        return
    journey.epochs_left = max(0, journey.epochs_left - 1)
    if journey.epochs_left > 0 and await mount_of(ctx, traveller.id) is not None:
        journey.epochs_left = max(0, journey.epochs_left - ctx.rules.beasts.mount_travel_epochs)
    if journey.epochs_left > 0:
        return
    result = await arrive(ctx, journey, traveller, route)
    journey.status = JourneyStatus.ARRIVED
    journey.end_epoch = ctx.epoch
    journey.result_entity_id = result.id if result is not None else None
    target = await ctx.session.get(WorldRow, journey.destination_world_id)
    if target is not None:
        await mark_world_discovered(ctx, target, f"{traveller.name}'s expedition arrived there")
    scene.arrivals.append(journey.id)


async def journeys(ctx: TickContext) -> list[int]:
    scene = JourneyScene(
        await RouteBook.load(ctx.session, ctx.rules, ctx.epoch),
        await KnowledgeMap.load(ctx.session),
        ctx.rng("journeys"),
        await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch),
    )
    statement = select(JourneyRow).where(JourneyRow.status.in_(list(LIVE_JOURNEYS))).order_by(JourneyRow.id)
    for journey in list(await ctx.session.scalars(statement)):
        await advance_journey(ctx, scene, journey)
    await ctx.session.flush()
    return scene.arrivals


async def kinship(session: AsyncSession, entity_id: int) -> set[int]:
    root, seen = entity_id, {entity_id}
    while True:
        parents = await active_bonds(session, [BondKind.DESCENDS_FROM], sources=[root])
        parent = next((bond.target_node_id for bond in parents if bond.target_node_id not in seen), None)
        if parent is None:
            break
        seen.add(parent)
        root = parent
    members, queue = {root}, deque([root])
    while queue:
        current = queue.popleft()
        for bond in await active_bonds(session, [BondKind.DESCENDS_FROM], targets=[current]):
            if bond.source_node_id not in members:
                members.add(bond.source_node_id)
                queue.append(bond.source_node_id)
    for bond in await active_bonds(session, [BondKind.RULES], sources=list(members)) + await active_bonds(session, [BondKind.RULES], targets=list(members)):
        members.update((bond.source_node_id, bond.target_node_id))
    return members | {entity_id}


async def landing_region(session: AsyncSession, rules: Rules, world_id: int) -> EntityRow | None:
    regions = await canon(session, [EntityType.REGION], world_id)
    if not regions:
        return None
    return max(regions, key=lambda region: (stat_or(region, FERTILITY_KEY, rules.travel.default_fertility), -region.id))


@dataclass
class Arrival:
    journey: JourneyRow
    traveller: EntityRow
    route: RouteRow
    region: EntityRow
    target: WorldRow
    colony: EntityRow | None = None
    contacts: list[str] = field(default_factory=list)
    contact_ids: list[int] = field(default_factory=list)
    subjugated: bool = False


async def _forget_on_river(ctx: TickContext, arrival: Arrival) -> None:
    costs = ctx.rules.travel_methods
    rng = ctx.rng(seed_of("river", arrival.journey.id))
    if arrival.route.method is not M.RIVER_OF_DEAD or not (arrival.journey.memory_lost or rng.chance(costs.river_memory_loss_pct)):
        return
    arrival.journey.memory_lost = True
    knowing = await active_bonds(ctx.session, [BondKind.KNOWS], sources=[arrival.traveller.id])
    forgotten = rng.sample(knowing, round(len(knowing) * costs.river_knowledge_loss_pct / PERCENT))
    bonds = BondRepository(ctx.session)
    for bond in forgotten:
        await bonds.deactivate(bond, ctx.epoch, "forgotten on the river of the dead")
    add_event(arrival.journey, ctx.epoch, JourneyEventKind.MEMORY_LOSS, f"the living forgot on the river; {len(forgotten)} kinds of knowledge were lost")


async def _dream_toll(ctx: TickContext, arrival: Arrival) -> bool:
    costs = ctx.rules.travel_methods
    if arrival.route.method is not M.DREAM_JOURNEY:
        return True
    rng = ctx.rng(seed_of("dream", arrival.journey.id))
    if arrival.journey.population > 0 and rng.chance(costs.dream_no_return_pct):
        lost = round(arrival.journey.population * costs.dream_no_return_share_pct / PERCENT)
        arrival.journey.population -= lost
        add_event(arrival.journey, ctx.epoch, JourneyEventKind.DREAM_NOT_RETURNED, f"{lost} dreamers never woke", loss=lost)
        return True
    if stat(arrival.traveller, POPULATION_KEY) is None and arrival.traveller.entity_type is EntityType.MORTAL and rng.chance(costs.dream_lone_no_return_pct):
        await retire(ctx.session, arrival.traveller, ctx.epoch, f"Epoch {ctx.epoch}: their soul never returned from the dream.")
        add_event(arrival.journey, ctx.epoch, JourneyEventKind.DREAM_NOT_RETURNED, "the dreamer's soul never returned")
        return False
    return True


async def _found_colony(ctx: TickContext, arrival: Arrival) -> EntityRow | None:
    travel = ctx.rules.travel
    journey, traveller = arrival.journey, arrival.traveller
    conquest = journey.intent is JourneyIntent.CONQUEST
    if arrival.target.atmosphere in HARSH_ATMOSPHERES and not await knows(ctx.session, traveller.id, KnowledgeBranch.VOID_LIVING):
        sky = "airless" if arrival.target.atmosphere.value == "none" else "toxic"
        await note(
            ctx,
            f"{traveller.name}'s colonists could not live under {arrival.target.name}'s {sky} sky; the colony died out in its first winter.",
            key="travel.colony_failed",
            ids=[traveller.id],
        )
        return None
    derived = None if journey.memory_lost else await Namer(ctx.session, ctx.rules).from_speaker(traveller.id, seed_of("colony", journey.id), NameKind.PLACE)
    kind = "conquest outpost" if conquest else "colony"
    colony = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=derived or f"{traveller.name} Colony",
            entity_type=EntityType.SETTLEMENT,
            body=f"{journey.population} travellers of {traveller.name} reached {arrival.target.name} and founded a {kind} in {arrival.region.name}.",
            stats=SettlementStats(
                population=journey.population,
                prosperity=travel.colony_prosperity,
                defense=travel.conquest_outpost_defense if conquest else travel.colony_defense,
                piety=stat_or(traveller, PIETY_KEY, travel.colony_default_piety),
            ),
            power=max(travel.colony_min_power, traveller.power_level - travel.colony_power_gap),
            world_id=arrival.target.id,
            location_id=arrival.region.id,
            subtype=kind,
            engine_kind=EngineKind.COLONY,
            flags=(EntityFlag.COLONY, EntityFlag.NAME_FROM_LANGUAGE) if derived else (EntityFlag.COLONY,),
        ),
    )
    await _bind_colony(ctx, arrival, colony)
    return colony


async def _bind_colony(ctx: TickContext, arrival: Arrival, colony: EntityRow) -> None:
    bonds = BondRepository(ctx.session)
    traveller = arrival.traveller
    await bonds.connect(BondDraft(colony.id, traveller.id, BondKind.DESCENDS_FROM, ctx.epoch, "its colony"))
    await bonds.connect(BondDraft(traveller.id, colony.id, BondKind.RULES, ctx.epoch, "colony beyond the worlds"))
    if not arrival.journey.memory_lost:
        language = await spoken_language(ctx.session, traveller.id)
        if language is not None:
            await bonds.connect(BondDraft(colony.id, language.id, BondKind.SPEAKS, ctx.epoch, "the tongue of the homeland"))
        patron = await bonds.patron(traveller.id)
        if patron is not None:
            await bonds.connect(BondDraft(colony.id, patron, BondKind.WORSHIPS, ctx.epoch, "the god of the homeland"))
    await bind_language_and_faith(ctx, colony, source=None if arrival.journey.memory_lost else traveller)


async def _contact(ctx: TickContext, arrival: Arrival, native: EntityRow) -> str:
    travel = ctx.rules.travel
    rng = ctx.rng(seed_of("contact", arrival.journey.id, native.id))
    traveller, journey = arrival.traveller, arrival.journey
    if journey.intent is JourneyIntent.CONQUEST and arrival.colony is not None and not arrival.subjugated:
        bonds = BondRepository(ctx.session)
        chance = travel.subjugation_chance - stat_or(native, "defense", 0) * PERCENT / travel.subjugation_defense_divisor
        if not await bonds.active_between(arrival.colony.id, native.id, [BondKind.RULES]) and rng.chance(max(0.0, chance)):
            await bonds.connect(BondDraft(arrival.colony.id, native.id, BondKind.RULES, ctx.epoch, "conquest across the worlds"))
            await change_relation(
                ctx, traveller.id, native.id, -travel.invasion_relation_loss, MemoryKind.FOUGHT_US, note="conquest", reverse=MemoryKind.CONQUERED_US
            )
            arrival.subjugated = True
            return f"{native.name} submitted without a fight"
    invasion = journey.intent is JourneyIntent.CONQUEST or (journey.intent is JourneyIntent.COLONY and rng.chance(travel.colony_invasion_chance))
    if invasion:
        invader = arrival.colony or traveller
        declared = await declare_war(ctx, invader.id, native.id, "first contact: invasion", cause=WarCause.CONQUEST_JOURNEY)
        await change_relation(ctx, traveller.id, native.id, -travel.invasion_relation_loss, MemoryKind.FOUGHT_US, note="invasion")
        return f"{native.name} saw them as invaders" if declared else f"{native.name} looked at them with hostility"
    alive = traveller.status is EntityStatus.CANON
    if alive and (journey.intent is JourneyIntent.TRADE or rng.chance(travel.contact_trade_chance)):
        bonds = BondRepository(ctx.session)
        await bonds.connect(BondDraft(traveller.id, native.id, BondKind.TRADES_WITH, ctx.epoch, f"interworld trade ({arrival.target.name})"))
        await change_relation(ctx, traveller.id, native.id, travel.contact_trade_relation, MemoryKind.TRADED_WITH, note="first contact")
        text = f"trade began with {native.name}"
        if rng.chance(travel.interworld_alliance_chance) and not await bonds.exists_between(traveller.id, native.id, BondKind.ALLY):
            await bonds.connect(BondDraft(traveller.id, native.id, BondKind.ALLY, ctx.epoch, f"interworld alliance ({arrival.target.name})"))
            await change_relation(ctx, traveller.id, native.id, travel.alliance_relation, MemoryKind.ALLIED_WITH, note="interworld alliance")
            text += f"; an interworld alliance was formed with {native.name}"
        exchanged = await cultural_contact(ctx, traveller, native, first_contact=True) + await cultural_contact(ctx, native, traveller, first_contact=True)
        if exchanged:
            text += f"; {exchanged} cultural gifts passed both ways"
        return text
    await change_relation(ctx, traveller.id, native.id, -travel.uneasy_relation_loss, MemoryKind.ILL_WILL, note="uneasy first contact")
    return f"{native.name} watched them uneasily"


async def first_contact(ctx: TickContext, arrival: Arrival) -> None:
    if arrival.colony is None and arrival.traveller.status is not EntityStatus.CANON:
        return
    kin = await kinship(ctx.session, arrival.traveller.id)
    bonds = BondRepository(ctx.session)
    natives = []
    for native in await canon(ctx.session, COMMUNITY_TYPES, arrival.target.id):
        if native.id in kin or (arrival.colony is not None and native.id == arrival.colony.id):
            continue
        if any([await bonds.exists_between(arrival.traveller.id, native.id, kind) for kind in (BondKind.TRADES_WITH, BondKind.ENEMY, BondKind.ALLY)]):
            continue
        natives.append(native)
    for native in natives[: ctx.rules.travel.contact_cap]:
        arrival.contacts.append(await _contact(ctx, arrival, native))
        arrival.contact_ids.append(native.id)


async def _explore_arrival(ctx: TickContext, arrival: Arrival) -> EntityRow | None:
    travel = ctx.rules.travel
    traveller = arrival.traveller
    shift_bounded(ctx.rules, traveller, CHARISMA_KEY, travel.exploration_charisma)
    seen = {bond.target_node_id for bond in await BondRepository(ctx.session).outgoing(traveller.id, BondKind.DISCOVERED)}
    originals = [
        item
        for item in await EntityRepository(ctx.session).with_flag(EntityFlag.ORIGINAL_RESOURCE)
        if item.world_id == arrival.target.id and item.id not in seen
    ]
    if originals:
        await connect(ctx.session, traveller.id, originals[0].id, BondKind.DISCOVERED, ctx.epoch, description=f"on the {arrival.target.name} expedition")
        add_event(arrival.journey, ctx.epoch, JourneyEventKind.DISCOVERY, f"they discovered {originals[0].name}")
    if arrival.journey.intent is JourneyIntent.EXPLORATION and ctx.rng(seed_of("land", arrival.journey.id)).chance(travel.exploration_land_chance):
        found = await find_land(
            ctx, LandSearch(arrival.target.id, explorer=traveller, near=arrival.region, pioneers=False, reason=f"on the {arrival.target.name} expedition")
        )
        if found is not None:
            add_event(arrival.journey, ctx.epoch, JourneyEventKind.DISCOVERY, f"they found {found.land.name}")
        return found.land if found is not None else None
    return None


async def arrive(ctx: TickContext, journey: JourneyRow, traveller: EntityRow, route: RouteRow) -> EntityRow | None:
    target = await ctx.session.get(WorldRow, journey.destination_world_id)
    region = await landing_region(ctx.session, ctx.rules, journey.destination_world_id) if target is not None else None
    if target is None or region is None:
        name = target.name if target is not None else "another world"
        await note(ctx, f"{traveller.name}'s travellers reached {name} but found no land to set foot on.", key="travel.no_land", ids=[traveller.id])
        return None
    arrival = Arrival(journey, traveller, route, region, target)
    await _forget_on_river(ctx, arrival)
    if not await _dream_toll(ctx, arrival):
        return None
    carried = await stowaway(ctx, journey.origin_world_id, region)
    if carried is not None:
        add_event(journey, ctx.epoch, JourneyEventKind.STOWAWAY, f"{carried.name} came ashore with them")
        await note(
            ctx, f"{traveller.name}'s ships carried a stowaway species to {target.name}; it became invasive there.", key="travel.stowaway", ids=[carried.id]
        )
    result: EntityRow | None = None
    if journey.intent in (JourneyIntent.COLONY, JourneyIntent.CONQUEST) and journey.population > 0:
        arrival.colony = await _found_colony(ctx, arrival)
        result = arrival.colony
    await first_contact(ctx, arrival)
    if journey.intent is JourneyIntent.PILGRIMAGE:
        site, offering = await reach_holy_site(ctx, ctx.rules, traveller, target.id, region)
        arrival.contacts.append(offering)
        result = result or site
    if journey.intent in (JourneyIntent.EXPLORATION, JourneyIntent.PILGRIMAGE):
        result = await _explore_arrival(ctx, arrival) or result
    if journey.intent is JourneyIntent.TRADE:
        add_prosperity(ctx.rules, traveller, ctx.rules.travel.trade_prosperity)
    await _arrival_note(ctx, arrival, result)
    return result


async def _arrival_note(ctx: TickContext, arrival: Arrival, result: EntityRow | None) -> None:
    journey, traveller = arrival.journey, arrival.traveller
    did = {
        JourneyIntent.COLONY: "founded a colony" if arrival.colony else "landed",
        JourneyIntent.CONQUEST: "founded a conquest outpost" if arrival.colony else "landed",
        JourneyIntent.TRADE: "opened trade",
        JourneyIntent.EXPLORATION: "explored",
        JourneyIntent.PILGRIMAGE: "reached their pilgrimage",
    }[journey.intent]
    contact = f" First contact: {'; '.join(arrival.contacts)}." if arrival.contacts else ""
    origin = await ctx.session.get(WorldRow, journey.origin_world_id)
    gap = time_difference(ctx.rules, traveller.name, origin, arrival.target, max(1, ctx.epoch - journey.start_epoch))
    tail = f" {gap}" if gap else ""
    ids = [traveller.id, arrival.region.id, *([result.id] if result else []), *arrival.contact_ids]
    await note(ctx, f"{traveller.name}'s travellers reached {arrival.target.name} and {did}.{contact}{tail}", key="travel.arrival", ids=ids, feed=None)


@reads(
    "knowledge.spread",
    "people.craft",
    "people.magic",
    "people.martiality",
    "people.piety",
    "people.population",
    "people.prosperity",
    "region.fertility",
    "settlement.defense",
    "settlement.piety",
    "settlement.population",
    "species.danger",
    "table.bonds",
    "table.calendars",
    "table.community_relations",
    "table.cosmos",
    "table.culture_values",
    "table.entity_flags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.forced_weather",
    "table.holder_levels",
    "table.journeys",
    "table.language_profiles",
    "table.lexemes",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.nodes",
    "table.personality_values",
    "table.place_environment",
    "table.pressures",
    "table.region_environment",
    "table.reverences",
    "table.routes",
    "table.sky_events",
    "table.traits",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
    "table.world_seasons",
)
@writes(
    "knowledge.spread",
    "people.piety",
    "people.population",
    "settlement.piety",
    "settlement.population",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.entity_flags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.journeys",
    "table.lexemes",
    "table.memories",
    "table.name_registry",
    "table.reverences",
    "table.routes",
    "table.sons",
)
async def travel_phase(ctx: TickContext) -> None:
    await hidden_routes(ctx)
    await route_knowledge(ctx)
    await spontaneous_expeditions(ctx)
    await bridge_collapse(ctx)
    await journeys(ctx)


async def _living(session: AsyncSession, entity_id: int) -> EntityRow:
    entity = await session.get(EntityRow, entity_id)
    if entity is None or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such living record.")
    return entity


async def send_expedition(session: AsyncSession, rules: Rules, traveller_id: int, route_id: int, intent: JourneyIntent, *, population: int = 0) -> JourneyRow:
    ctx = await manual_context(session, "expedition", rules, key=f"{traveller_id}:{route_id}")
    traveller = await _living(session, traveller_id)
    route = await session.get(RouteRow, route_id)
    if route is None:
        raise NotFoundError("No such route.")
    if traveller.entity_type in COMMUNITY_TYPES:
        capability = {JourneyIntent.COLONY: TierCapability.COLONY, JourneyIntent.CONQUEST: TierCapability.CONQUEST}.get(intent, TierCapability.EXPEDITION)
        if not unlocked(rules, traveller.civ_tier or 0, capability):
            raise ValidationFailedError(f"{traveller.name} has not grown enough as a civilization for this kind of expedition.")
    problem = await can_use_route(session, rules, ctx.epoch, traveller, route)
    if problem is not None:
        raise ValidationFailedError(problem)
    vehicle_id = route.vehicle_entity_id
    vehicle = await session.get(EntityRow, vehicle_id) if vehicle_id is not None else None
    journey = await start_journey(ctx, JourneySpec(traveller, route, intent, population, vehicle))
    await note(
        ctx,
        f"{traveller.name} set out for {await world_name(session, journey.destination_world_id)} ({INTENT_SENT[intent]}).",
        key="travel.expedition_ordered",
        ids=[traveller.id],
    )
    return journey


async def reveal_route(session: AsyncSession, rules: Rules, route_id: int, by: str) -> str:
    return await reveal_hidden_route(await manual_context(session, "reveal", rules, key=str(route_id)), route_id, by)


async def teach_route_knowledge(session: AsyncSession, rules: Rules, community_id: int, route_id: int) -> EntityRow | None:
    ctx = await manual_context(session, "teach_route", rules, key=f"{community_id}:{route_id}")
    route = await session.get(RouteRow, route_id)
    if route is None:
        raise NotFoundError("No such route.")
    return await teach_route(ctx, await _living(session, community_id), route)


async def sever_by_hand(session: AsyncSession, rules: Rules, route_id: int, by: str, *, duration: int | None = None) -> str:
    ctx = await manual_context(session, "sever", rules, key=str(route_id))
    return (await sever_route(ctx, route_id, duration=duration, by=by)).text


async def stitch_by_hand(session: AsyncSession, rules: Rules, route_id: int, by: str) -> str:
    return await stitch_route(await manual_context(session, "stitch", rules, key=str(route_id)), route_id, by)


async def run_travel_phase(session: AsyncSession, rules: Rules) -> None:
    await travel_phase(await manual_context(session, "travel", rules))


PHASES = (Phase("travel", travel_phase),)
