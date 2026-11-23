from typing import Any

from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.fortune.profiles import fortune_of, shift_fortune
from aerona.engine.kinds.society import mortals_may_found
from aerona.engine.mythic.heroquests import renown_of
from aerona.engine.phases.factions import decree_faction
from aerona.engine.sacred.places import town_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


async def take_care(call: MortalCall, _args: ToolInput) -> str:
    table = call.rules.fortune
    if held(call.me.id):
        fail(MortalResult.CARE_DECLINED, why="your own course is held")
    if await points_of(call.session, call.me) < table.care_cost:
        fail(MortalResult.CARE_DECLINED, why="you cannot spare what care would cost")
    await shift_points(call.session, call.me, -table.care_cost)
    await shift_fortune(call.tick, call.me.id, table.care_strength, FortuneSourceKind.CARE, epochs=1)
    await call.record("tools.mortal.took_care", roles={IncidentRole.ACTOR: call.me.id}, facts={"cost": table.care_cost, "fortune": table.care_strength})
    return result(MortalResult.CARE_TAKEN, fortune=await fortune_of(call.tick, call.me.id))


class FoundFactionInput(ToolInput):
    kind: FactionKind


async def found_faction(call: MortalCall, args: FoundFactionInput) -> str:
    table = call.rules.factions
    town = await town_of(call.session, call.me)
    if town is None or held(town.id):
        fail(MortalResult.FACTION_DECLINED, why="you stand in no town")
    if await renown_of(call.tick, call.me.id) < table.found_renown:
        fail(MortalResult.FACTION_DECLINED, why="too few know your name to follow you")
    if await points_of(call.session, call.me) < table.found_cost:
        fail(MortalResult.FACTION_DECLINED, why="you cannot pay what founding it would cost")
    if not await mortals_may_found(call.session, town, args.kind):
        fail(MortalResult.FACTION_DECLINED, why="no mortal founds a body of that kind among your people")
    try:
        faction = await decree_faction(call.tick, town.id, args.kind)
    except (ConflictError, ValidationFailedError) as error:
        fail(MortalResult.FACTION_DECLINED, why=str(error).rstrip("."))
    await shift_points(call.session, call.me, -table.found_cost)
    profile = await call.session.get(FactionProfileRow, faction.id)
    if profile is not None:
        profile.leader_entity_id = call.me.id
    call.target(faction.id)
    await call.record(
        "tools.mortal.founded_faction",
        roles={IncidentRole.LEADER: call.me.id, IncidentRole.PRODUCT: faction.id, IncidentRole.PLACE: town.id},
        facts={"faction": args.kind, "cost": table.found_cost},
        place=town.id,
    )
    return result(MortalResult.FACTION_FOUNDED, name=faction.name, town=town.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.TAKE_CARE, AgentKind.MORTAL, ToolInput, meta, take_care),
        ToolSpec(MortalToolId.FOUND_FACTION, AgentKind.MORTAL, FoundFactionInput, meta, found_faction),
    ]
