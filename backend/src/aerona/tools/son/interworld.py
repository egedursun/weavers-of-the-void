from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
CLOSE_MAX = 5


class CloseTheWayInput(ToolInput):
    route_id: int
    epochs: int = Field(ge=1, le=CLOSE_MAX)
    reason: Reason


async def close_the_way(call: SonCall, args: CloseTheWayInput) -> str:
    route = await call.session.get(RouteRow, args.route_id)
    if route is None or not route.active:
        fail(SonResult.CLOSING_REFUSED, why="there is no such way")
    if "temp_closed_until_epoch" in (route.locked or []):
        fail(SonResult.CLOSING_REFUSED, why="that way is held as it is")
    route.temp_closed_until_epoch = max(route.temp_closed_until_epoch or 0, call.tick.epoch + args.epochs)
    first = await call.session.get(WorldRow, route.world_a_id)
    second = await call.session.get(WorldRow, route.world_b_id)
    await call.record(
        "travel.way_closed", roles={IncidentRole.ORIGIN: route.world_a_id, IncidentRole.DESTINATION: route.world_b_id}, facts={"epochs": args.epochs}
    )
    return result(
        SonResult.WAY_CLOSED,
        first=first.name if first is not None else "one world",
        second=second.name if second is not None else "another",
        until=route.temp_closed_until_epoch,
    )


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.CLOSE_THE_WAY, AgentKind.SON, CloseTheWayInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), close_the_way)]
