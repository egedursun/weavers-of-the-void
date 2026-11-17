from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.museum import HoardKind
from aerona.engine.museums.control import found_garden, found_hoard
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class FoundMuseumInput(ToolInput):
    town_id: int
    reason: Reason


class LayOutGardenInput(ToolInput):
    town_id: int
    kind: GardenKind
    reason: Reason


async def town_in_reach(call: SonCall, town_id: int, refused: SonResult) -> Any:
    town = await living_entity(call.session, town_id)
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        fail(refused, why="there is no such town")
    await ensure_in_reach(call, town)
    if held(town.id):
        fail(refused, why="a stronger hand holds that town")
    return town


async def found_museum(call: SonCall, args: FoundMuseumInput) -> str:
    town = await town_in_reach(call, args.town_id, SonResult.MUSEUM_REFUSED)
    cost = call.rules.museums.son_cost
    require_essence(call, cost)
    await found_hoard(call.tick, town.id, HoardKind.MUSEUM)
    call.spend_essence(cost)
    call.target(town.id)
    await call.record(
        "tools.son.found_museum",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: town.id},
        facts={"town": str(town.name), "reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.MUSEUM_FOUNDED, town=town.name)


async def lay_out_garden(call: SonCall, args: LayOutGardenInput) -> str:
    town = await town_in_reach(call, args.town_id, SonResult.GARDEN_REFUSED)
    cost = call.rules.gardens.son_cost
    require_essence(call, cost)
    await found_garden(call.tick, town.id, args.kind)
    call.spend_essence(cost)
    call.target(town.id)
    told = args.kind.value.replace("_", " ")
    await call.record(
        "tools.son.lay_out_garden",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: town.id},
        facts={"town": str(town.name), "kind": str(told), "reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.GARDEN_LAID_OUT, town=town.name, kind=told)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.FOUND_MUSEUM, AgentKind.SON, FoundMuseumInput, meta, found_museum),
        ToolSpec(SonToolId.LAY_OUT_GARDEN, AgentKind.SON, LayOutGardenInput, meta, lay_out_garden),
    ]
