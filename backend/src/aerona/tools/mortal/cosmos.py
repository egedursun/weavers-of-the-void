from typing import Any

from sqlalchemy import select

from aerona.catalog.civilization import unlocked
from aerona.catalog.life.tools import INTENT_TIERS, WAY_KNOWLEDGE
from aerona.catalog.life_traits import JOURNEY_INTENT_TRAITS, having
from aerona.catalog.rarities import name_similarity_policy
from aerona.catalog.travel import JOURNEY_INTENT_LABELS
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.life_traits import JourneyIntentTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import Commodity, KnowledgeBranch
from aerona.domain.enums.travel import VehicleKind
from aerona.engine.cosmos.routes import LIVE_JOURNEYS, JourneySpec, can_use_route, method_label, start_journey
from aerona.engine.cosmos.vessels import owned_vessels, set_vessel_kind
from aerona.engine.phases.exploration import SearchStatus, land_stats, pioneers, position_region, record_intuition, route_method, search_route
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.primitives.stats import stat
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.errors import RejectionError
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail, require_canon
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import ExpeditionInput, ExploreInput, FindRouteInput, LandKind, ShipInput
from aerona.tools.mortal.support import (
    MortalCreation,
    civilization_tier,
    create_record,
    first_stat,
    i_know,
    name_free,
    near,
    refuse_level,
)

PERCENT = 100
SETTLERS = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
EXPLORER_WITS = ("intellect", "craft")
SHIP_CRAFT = ("craft", "wealth")
CROWD_INTENTS = having(JOURNEY_INTENT_TRAITS, JourneyIntentTrait.CROWD_INTENTS)


def clamp(value: float) -> int:
    return max(0, min(PERCENT, round(value)))


async def find_route(call: MortalCall, args: FindRouteInput) -> str:
    if await route_method(call.tick, call.me) is None:
        fail(MortalResult.NO_ROUTE_METHOD)
    search = await search_route(call.tick, call.me, args.how)
    if search.status is SearchStatus.ROUTE and search.route is not None and search.target is not None:
        route = search.route
        if search.vehicle is not None:
            call.remember_creation(search.vehicle.id)
        call.target(search.target.id)
        await call.record(
            "tools.mortal.route_found",
            roles={
                IncidentRole.ACTOR: call.me.id,
                IncidentRole.DESTINATION: search.target.id,
                IncidentRole.INSTRUMENT: search.vehicle.id if search.vehicle is not None else None,
            },
            facts={"method": route.method, "epochs": route.duration_epochs, "danger": route.danger},
        )
        return result(MortalResult.ROUTE_FOUND, id=route.id, method=method_label(route.method), epochs=route.duration_epochs, danger=route.danger)
    if search.status is SearchStatus.INTUITION:
        await record_intuition(call.tick, call.me, args.how, search.method)
        await call.record("tools.mortal.route_sensed", roles={IncidentRole.ACTOR: call.me.id}, facts={"method": search.method, "how": args.how})
        return result(MortalResult.WORLD_SENSED)
    await call.record("tools.mortal.route_not_found", roles={IncidentRole.ACTOR: call.me.id}, facts={"how": args.how})
    return result(MortalResult.NO_ROUTE)


async def _explore_parent(call: MortalCall, args: ExploreInput) -> EntityRow | None:
    if args.kind is LandKind.REGION:
        return None
    parent_id = args.location_id if args.location_id is not None else (await call.atlas()).top_region(call.me.id)
    if parent_id is None:
        fail(MortalResult.PLACE_NEAR)
    parent = await require_canon(call.session, parent_id)
    if parent.entity_type is not EntityType.REGION or not await near(call, parent):
        fail(MortalResult.PLACE_NEAR)
    return parent


async def explore_land(call: MortalCall, args: ExploreInput) -> str:
    exploration = call.rules.exploration
    await call.within_limit(TurnCounter.EXPLORATIONS, exploration.tool_per_epoch, "exploration.tool_per_epoch", MortalResult.EXPLORE_LIMIT)
    await name_free(call, args.name)
    similar = await NameRepository(call.session).similar_name(args.name, name_similarity_policy(call.rules))
    if similar is not None:
        fail(MortalResult.NAME_TOO_SIMILAR, name=args.name, other=similar)
    parent = await _explore_parent(call, args)
    kind = EntityType.REGION if args.kind is LandKind.REGION else EntityType.PLACE
    await refuse_level(call, parent, args.stratum if kind is EntityType.PLACE else None, kind)
    await call.bump(TurnCounter.EXPLORATIONS)
    knows_way = any([await i_know(call, branch) for branch in WAY_KNOWLEDGE])
    wits = first_stat(call.me, EXPLORER_WITS, call.rules.mortal_tools.default_stat)
    roll = call.die(PERCENT, "explore") + round(wits / call.rules.mortal_tools.route_intellect_divisor) + (exploration.tool_knowledge_bonus if knows_way else 0)
    if roll < exploration.tool_success_threshold:
        await call.record(
            "tools.mortal.explore_failed", roles={IncidentRole.ACTOR: call.me.id}, facts={"roll": roll, "needed": exploration.tool_success_threshold}
        )
        return result(MortalResult.EXPLORE_FAILED, roll=roll, needed=exploration.tool_success_threshold)
    stats = land_stats(call.tick, kind, call.rng("land")).model_dump(exclude={"kind"}, exclude_none=True)
    land = await create_record(
        call,
        MortalCreation(
            args.name,
            kind,
            args.description,
            subtype=args.subtype,
            stats=stats,
            location_id=parent.id if parent is not None else None,
            stratum=args.stratum if kind is EntityType.PLACE else None,
            image_prompt=args.image_prompt,
        ),
    )
    if kind is EntityType.REGION:
        origin = (await call.atlas()).top_region(call.me.id)
        await position_region(call.tick, land, await call.session.get(EntityRow, origin) if origin is not None else None)
    await EntityRepository(call.session).add_flag(land.id, EntityFlag.DISCOVERY, call.epoch)
    await BondRepository(call.session).connect(BondDraft(call.me.id, land.id, BondKind.DISCOVERED, call.epoch))
    settlement = await pioneers(call.tick, call.me, land) if args.settle and call.me.entity_type in SETTLERS else None
    if settlement is not None:
        call.remember_creation(settlement.id)
    await call.record(
        "tools.mortal.explored",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PRODUCT: land.id, IncidentRole.PLACE: parent.id if parent is not None else None},
        facts={"land_kind": kind, "settlement": settlement.id if settlement is not None else None, "roll": roll},
        place=parent.id if parent is not None else land.id,
    )
    return result(
        MortalResult.EXPLORED,
        id=land.id,
        name=land.name,
        settle=args.settle,
        settlement=settlement.name if settlement is not None else "",
        settlement_id=settlement.id if settlement is not None else 0,
    )


async def build_ship(call: MortalCall, args: ShipInput) -> str:
    tools = call.rules.mortal_tools
    if not await i_know(call, KnowledgeBranch.SHIPBUILDING):
        fail(MortalResult.SHIPBUILDING_REQUIRED)
    await name_free(call, args.name)
    ore = await stock(call.session, call.rules, call.me.id, Commodity.ORE)
    metallurgy = tools.ship_metallurgy_bonus if await i_know(call, KnowledgeBranch.METALLURGY) else 0
    craft = first_stat(call.me, SHIP_CRAFT, tools.default_stat) + ore / tools.ship_miners_divisor + metallurgy
    stats = {
        "speed": clamp(tools.ship_speed_base + craft / tools.ship_speed_craft_divisor + call.die(tools.ship_speed_die)),
        "range": clamp(tools.ship_range_base + call.die(tools.ship_range_die)),
        "crew": tools.ship_crew_base + call.die(tools.ship_crew_die),
        "armor": clamp(tools.ship_armor_base + craft / tools.ship_armor_craft_divisor + call.die(tools.ship_armor_die)),
        "strangeness": clamp(call.die(tools.ship_strangeness_die)),
    }
    subtype = lines.SHIP_SUBTYPE.format(suffix=lines.DIALECT_SUFFIX.format(subtype=args.subtype) if args.subtype else "")
    home = call.me.id if call.me.entity_type is EntityType.SETTLEMENT else call.me.location_id
    ship = await create_record(
        call, MortalCreation(args.name, EntityType.VESSEL, args.description, subtype=subtype, stats=stats, location_id=home, image_prompt=args.image_prompt)
    )
    await set_vessel_kind(call.session, ship.id, VehicleKind.SHIP)
    await BondRepository(call.session).connect(BondDraft(call.me.id, ship.id, BondKind.OWNS, call.epoch, lines.SHIPYARD))
    await shift_stock(call.session, call.rules, call.me.id, Commodity.ORE, -tools.ship_miners_cost, epoch=call.epoch, flow=GoodsFlow.TOOL)
    await call.record(
        "tools.mortal.ship", roles={IncidentRole.MAKER: call.me.id, IncidentRole.PRODUCT: ship.id}, facts={"ore_spent": tools.ship_miners_cost}, place=home
    )
    return result(MortalResult.SHIP_READY, id=ship.id, name=ship.name)


async def _expedition_route(call: MortalCall, route_id: int) -> RouteRow:
    route = await call.session.get(RouteRow, route_id)
    world = call.me.world_id
    if route is None or not route.known or world not in (route.world_a_id, route.world_b_id):
        fail(MortalResult.NO_KNOWN_ROUTE)
    problem = await can_use_route(call.session, call.rules, call.epoch, call.me, route)
    if problem is not None:
        raise RejectionError(problem)
    return route


async def _vessel(call: MortalCall, vessel_id: int | None) -> EntityRow | None:
    bonds = BondRepository(call.session)
    if vessel_id is not None:
        vessel = await call.session.get(EntityRow, vessel_id)
        if vessel is None or vessel.entity_type is not EntityType.VESSEL or not await bonds.exists_between(call.me.id, vessel.id, BondKind.OWNS):
            fail(MortalResult.VESSEL_NOT_YOURS)
        return vessel
    ships = await owned_vessels(call.session, call.me.id, VehicleKind.SHIP)
    return ships[0] if ships else None


def _travellers(call: MortalCall, percent: int | None) -> int:
    tools = call.rules.mortal_tools
    share = min(tools.expedition_max_pct, percent or tools.expedition_default_pct)
    population, followers = stat(call.me, "population"), stat(call.me, "followers")
    if population is not None:
        return round(population * share / PERCENT)
    if followers is not None:
        return round(followers * share / PERCENT)
    return 1


async def launch_expedition(call: MortalCall, args: ExpeditionInput) -> str:
    tools = call.rules.mortal_tools
    capability = INTENT_TIERS.get(args.intent)
    if capability is not None and not unlocked(call.rules, await civilization_tier(call.session, call.me), capability):
        fail(MortalResult.INTENT_TIER, intent=JOURNEY_INTENT_LABELS[args.intent].lower())
    route = await _expedition_route(call, args.route_id)
    travelling = await call.session.scalar(
        select(JourneyRow.id).where(JourneyRow.traveller_entity_id == call.me.id, JourneyRow.status.in_(list(LIVE_JOURNEYS))).limit(1)
    )
    if travelling is not None:
        fail(MortalResult.ALREADY_TRAVELLING)
    vessel = await _vessel(call, args.vessel_id)
    people = _travellers(call, args.percent)
    if args.intent in CROWD_INTENTS and people < tools.expedition_min_people:
        fail(MortalResult.TOO_FEW_FOR_EXPEDITION)
    journey = await start_journey(call.tick, JourneySpec(call.me, route, args.intent, people, vessel))
    call.target(journey.destination_world_id)
    await call.record(
        "tools.mortal.expedition",
        roles={
            IncidentRole.ACTOR: call.me.id,
            IncidentRole.DESTINATION: journey.destination_world_id,
            IncidentRole.INSTRUMENT: vessel.id if vessel is not None else None,
        },
        facts={"intent": args.intent, "travellers": journey.population, "epochs": journey.epochs_left},
        cause=journey.incident_id,
    )
    return result(MortalResult.EXPEDITION_STARTED, epochs=journey.epochs_left)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    standard = mortal_standard_action
    return [
        ToolSpec(MortalToolId.FIND_ROUTE, mortal, FindRouteInput, ToolMeta(ActionKind.DISCOVER_ROUTE, standard), find_route),
        ToolSpec(MortalToolId.EXPLORE_LAND, mortal, ExploreInput, ToolMeta(ActionKind.EXPLORE_LAND, standard), explore_land),
        ToolSpec(MortalToolId.BUILD_SHIP, mortal, ShipInput, ToolMeta(ActionKind.BUILD_SHIP, standard), build_ship),
        ToolSpec(MortalToolId.LAUNCH_EXPEDITION, mortal, ExpeditionInput, ToolMeta(ActionKind.SET_OUT, standard), launch_expedition),
    ]
