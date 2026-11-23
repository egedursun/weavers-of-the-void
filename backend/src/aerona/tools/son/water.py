from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import several
from aerona.db.tables.water import MONTHS
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.terms import explaining_alone, term
from aerona.engine.water.ice import cryosphere_of
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class MoveIceInput(ToolInput):
    region_id: int
    change: Annotated[int, Field(ge=-MONTHS, le=MONTHS)]
    reason: Reason


async def move_ice(call: SonCall, args: MoveIceInput) -> str:
    region = await living_entity(call.session, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        fail(SonResult.ICE_REFUSED, why="there is no such land")
    await ensure_in_reach(call, region)
    if held(region.id):
        fail(SonResult.ICE_REFUSED, why="it is held")
    most = call.rules.water_and_ice.ice_change_max
    if abs(args.change) > most:
        fail(SonResult.ICE_REFUSED, why=f"no god moves more than {several(most, 'month', 'months')} of ice at once")
    row = await cryosphere_of(call.tick, region.id)
    if "ice_shift" in row.locked:
        fail(SonResult.ICE_REFUSED, why="this ice is held")
    with explaining_alone():
        term("water_and_ice.god_ice", args.change, source_node_id=region.id)
        row.ice_shift = clamp_int(row.ice_shift + args.change, -MONTHS, MONTHS)
        row.ice_months = clamp_int(row.ice_months + args.change, 0, MONTHS)
    call.target(region.id)
    await call.record(
        "tools.son.move_ice",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"change": args.change, "reason": args.reason},
        place=region.id,
        kind=ChronicleKind.CLIMATE,
    )
    return result(SonResult.ICE_MOVED, region=region.name, months=row.ice_months)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.MOVE_ICE, AgentKind.SON, MoveIceInput, meta, move_ice)]
