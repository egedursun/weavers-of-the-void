from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.engine.agentless_conditions.arise import ConditionTally
from aerona.engine.agentless_conditions.course import eased, named_of
from aerona.engine.body.state import refresh
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class EaseBodyInput(ToolInput):
    being_id: int
    condition_id: int
    reason: Reason


async def ease_body(call: SonCall, args: EaseBodyInput) -> str:
    being = await call.session.get(EntityRow, args.being_id)
    row = await call.session.get(ConditionRow, args.condition_id)
    if being is None or row is None or row.bearer_node_id != being.id or row.ended_epoch is not None:
        fail(SonResult.BODY_REFUSED, why="that being bears no such condition")
    await ensure_in_reach(call, being)
    if held(being.id):
        fail(SonResult.BODY_REFUSED, why="a stronger hand holds that body as it is")
    kind = await call.session.get(AgentlessConditionRow, row.kind_id) if row.kind_id is not None else None
    await eased(call.tick, row, being, kind, ConditionTally())
    await refresh(call.session, call.rules, being, call.tick.epoch)
    call.target(being.id)
    return result(SonResult.BODY_EASED, name=being.name, condition=named_of(row, kind), severity=row.severity)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.EASE_BODY, AgentKind.SON, EaseBodyInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), ease_body)]
