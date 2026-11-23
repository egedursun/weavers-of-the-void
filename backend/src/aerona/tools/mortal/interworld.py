from typing import Any

from aerona.core.grammar import spoken
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.interworld import MigrationCause
from aerona.engine.cosmos.routes import touches
from aerona.engine.interworld.book import InterworldTally, route_between, route_open
from aerona.engine.interworld.campaigns import launch
from aerona.engine.interworld.migrations import begin, blocked
from aerona.engine.interworld.orbit import contest
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.monetary import controls


class LaunchCampaignInput(ToolInput):
    attacker_id: int
    target_world_id: int
    route_id: int
    army_id: int


class ContestOrbitInput(ToolInput):
    world_id: int
    fleet_id: int


class LeadMigrationInput(ToolInput):
    community_id: int
    to_world_id: int
    cause: MigrationCause


async def open_way(call: MortalCall, route_id: int, first: int, second: int) -> RouteRow:
    route = await call.session.get(RouteRow, route_id)
    if route is None or not touches(route, first) or not touches(route, second) or first == second:
        fail(MortalResult.CROSSING_REFUSED, why="that way does not join those two worlds")
    if not await route_open(call.tick, route):
        fail(MortalResult.CROSSING_REFUSED, why="that way is closed")
    return route


async def own_army(call: MortalCall, army_id: int, owner_id: int) -> ArmyRow:
    row = await call.session.get(ArmyRow, army_id)
    army = await living_entity(call.session, army_id)
    if row is None or army is None or row.owner_entity_id != owner_id or row.disbanded_epoch is not None:
        fail(MortalResult.CROSSING_REFUSED, why="that host is not one it holds")
    if held(army_id):
        fail(MortalResult.CROSSING_REFUSED, why="a god holds that host as it is")
    return row


async def launch_campaign_tool(call: MortalCall, args: LaunchCampaignInput) -> str:
    attacker = await living_entity(call.session, args.attacker_id)
    if attacker is None or not await controls(call, attacker.id) or held(attacker.id):
        fail(MortalResult.CROSSING_REFUSED, why="only the one who leads a realm sends its hosts")
    await own_army(call, args.army_id, attacker.id)
    army = await living_entity(call.session, args.army_id)
    if army is None or army.world_id is None or await call.session.get(WorldRow, args.target_world_id) is None:
        fail(MortalResult.CROSSING_REFUSED, why="there is no such world to reach")
    route = await open_way(call, args.route_id, army.world_id, args.target_world_id)
    row = await launch(call.tick, attacker, army, args.target_world_id, route, tally=InterworldTally())
    call.target(attacker.id)
    return result(MortalResult.CAMPAIGN_LAUNCHED, forces=row.forces, transit=row.transit_left)


async def contest_orbit_tool(call: MortalCall, args: ContestOrbitInput) -> str:
    row = await call.session.get(ArmyRow, args.fleet_id)
    if row is None or not await controls(call, row.owner_entity_id):
        fail(MortalResult.CROSSING_REFUSED, why="only the one who leads its realm commands that host")
    await own_army(call, args.fleet_id, row.owner_entity_id)
    army = await living_entity(call.session, args.fleet_id)
    if army is None or army.world_id != args.world_id:
        fail(MortalResult.CROSSING_REFUSED, why="the host must be at that world to fight for the space around it")
    won = await contest(call.tick, args.world_id, row.owner_entity_id, army, InterworldTally())
    call.target(row.owner_entity_id)
    return result(MortalResult.ORBIT_CONTESTED, outcome="won the space around it" if won else "was driven back")


async def lead_migration_tool(call: MortalCall, args: LeadMigrationInput) -> str:
    community = await living_entity(call.session, args.community_id)
    if community is None or community.entity_type is not EntityType.SETTLEMENT or community.world_id is None:
        fail(MortalResult.CROSSING_REFUSED, why="a movement between worlds sets out from a settlement")
    if call.me.location_id != community.id and not await controls(call, community.id):
        fail(MortalResult.CROSSING_REFUSED, why="you lead the people of the place you live in or rule")
    if held(community.id):
        fail(MortalResult.CROSSING_REFUSED, why="that place is held as it is")
    route = await route_between(call.tick, community.world_id, args.to_world_id)
    if route is None:
        fail(MortalResult.CROSSING_REFUSED, why="no open way joins those worlds")
    problem = await blocked(call.tick, community, route)
    if problem is not None:
        fail(MortalResult.CROSSING_REFUSED, why=problem)
    row = await begin(call.tick, community, args.to_world_id, args.cause, route, tally=InterworldTally())
    call.target(community.id)
    return result(MortalResult.MIGRATION_LED, cause=spoken(args.cause), per_epoch=row.per_epoch, reception=spoken(row.reception))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.LAUNCH_CAMPAIGN, AgentKind.MORTAL, LaunchCampaignInput, act, launch_campaign_tool),
        ToolSpec(MortalToolId.CONTEST_ORBIT, AgentKind.MORTAL, ContestOrbitInput, act, contest_orbit_tool),
        ToolSpec(MortalToolId.LEAD_MIGRATION, AgentKind.MORTAL, LeadMigrationInput, act, lead_migration_tool),
    ]
