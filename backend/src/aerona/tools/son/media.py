from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.media import MediaOutletRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
LEAN = 100


class SwayOutletInput(ToolInput):
    outlet_id: int
    stance: ValueAxis
    lean: int = Field(ge=-LEAN, le=LEAN)
    reason: Reason


async def sway_outlet(call: SonCall, args: SwayOutletInput) -> str:
    outlet = await call.session.get(MediaOutletRow, args.outlet_id)
    seat = await living_entity(call.session, outlet.seat_entity_id) if outlet is not None else None
    if outlet is None or seat is None:
        fail(SonResult.MEDIA_REFUSED, why="there is no such outlet")
    await ensure_in_reach(call, seat)
    if held(outlet.owner_node_id) or held(seat.id) or {"stance", "lean"} & set(outlet.locked or []):
        fail(SonResult.MEDIA_REFUSED, why="it is held")
    outlet.stance, outlet.lean = args.stance, args.lean
    call.target(seat.id)
    await call.record(
        "media.outlet_swayed",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.TARGET: outlet.owner_node_id},
        facts={"outlet": outlet.name, "reason": args.reason},
        place=seat.id,
    )
    return result(SonResult.OUTLET_SWAYED, outlet=outlet.name, stance=spoken(args.stance), lean=args.lean)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.SWAY_OUTLET, AgentKind.SON, SwayOutletInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), sway_outlet)]
