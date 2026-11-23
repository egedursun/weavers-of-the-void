from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.leader_cults import LeaderCultRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.leader_cults import CultFate
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
SWAY_MAX = 30


class SwayCultInput(ToolInput):
    cult_id: int
    intensity_change: int = Field(ge=-SWAY_MAX, le=SWAY_MAX)
    reason: Reason


async def sway_cult(call: SonCall, args: SwayCultInput) -> str:
    cult = await call.session.get(LeaderCultRow, args.cult_id)
    leader = await living_entity(call.session, cult.leader_node_id) if cult is not None else None
    if cult is None or leader is None or cult.fate is not CultFate.LIVING:
        fail(SonResult.CULT_REFUSED, why="there is no such living cult")
    await ensure_in_reach(call, leader)
    if held(leader.id) or "intensity" in (cult.locked or []) or not args.intensity_change:
        fail(SonResult.CULT_REFUSED, why="that cult is held, or nothing would change")
    cult.intensity = clamp_int(cult.intensity + args.intensity_change, 0, PERCENT)
    call.target(leader.id)
    await call.record("cult.swayed", roles={IncidentRole.SUBJECT: leader.id}, facts={"change": args.intensity_change, "intensity": cult.intensity})
    return result(SonResult.CULT_SWAYED, leader=leader.name, intensity=cult.intensity)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.SWAY_CULT, AgentKind.SON, SwayCultInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), sway_cult)]
