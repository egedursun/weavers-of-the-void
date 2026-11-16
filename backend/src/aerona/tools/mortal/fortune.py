from typing import Any

from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.faction import FoundableFaction
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.fortune.profiles import fortune_of, shift_fortune
from aerona.engine.mythic.heroquests import renown_of
from aerona.engine.phases.factions import FOUNDED_AS, decree_faction
from aerona.engine.sacred.places import town_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines


async def take_care(call: MortalCall, _args: ToolInput) -> str:
    table = call.rules.fortune
    if held(call.me.id):
        fail(MortalResult.CARE_DECLINED, why="a stronger hand holds you")
    if await points_of(call.session, call.me) < table.care_cost:
        fail(MortalResult.CARE_DECLINED, why="you cannot spare what care would cost")
    await shift_points(call.session, call.me, -table.care_cost)
    await shift_fortune(call.tick, call.me.id, table.care_strength, FortuneSourceKind.CARE, epochs=1)
    await call.chronicle(ChronicleKind.CULTURE, lines.TOOK_CARE, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.CARE_TAKEN, fortune=await fortune_of(call.tick, call.me.id))


class FoundFactionInput(ToolInput):
    kind: FoundableFaction


async def found_faction(call: MortalCall, args: FoundFactionInput) -> str:
    table = call.rules.factions
    town = await town_of(call.session, call.me)
    if town is None or held(town.id):
        fail(MortalResult.FACTION_DECLINED, why="you stand in no town")
    if await renown_of(call.tick, call.me.id) < table.found_renown:
        fail(MortalResult.FACTION_DECLINED, why="too few know your name to follow you")
    if await points_of(call.session, call.me) < table.found_cost:
        fail(MortalResult.FACTION_DECLINED, why="you cannot pay what founding it would cost")
    try:
        faction = await decree_faction(call.tick, town.id, FOUNDED_AS[args.kind])
    except (ConflictError, ValidationFailedError) as error:
        fail(MortalResult.FACTION_DECLINED, why=str(error).rstrip("."))
    await shift_points(call.session, call.me, -table.found_cost)
    profile = await call.session.get(FactionProfileRow, faction.id)
    if profile is not None:
        profile.leader_entity_id = call.me.id
    call.target(faction.id)
    await call.chronicle(
        ChronicleKind.CIVILIZATION, lines.FOUNDED_FACTION, entity_ids=[call.me.id, faction.id, town.id], me=call.me.name, name=faction.name, town=town.name
    )
    return result(MortalResult.FACTION_FOUNDED, name=faction.name, town=town.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.TAKE_CARE, AgentKind.MORTAL, ToolInput, meta, take_care),
        ToolSpec(MortalToolId.FOUND_FACTION, AgentKind.MORTAL, FoundFactionInput, meta, found_faction),
    ]
