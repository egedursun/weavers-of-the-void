from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.living.blessing import bless_line, curse_line, line_in_world
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class LineJudgementInput(ToolInput):
    line_id: int
    reason: Reason


async def bless_line_tool(call: SonCall, args: LineJudgementInput) -> str:
    line = await line_in_world(call.tick, args.line_id, call.son.current_world_id)
    if line is None:
        fail(SonResult.LINE_JUDGEMENT_REFUSED, why="there is no such line in your world")
    await bless_line(call.tick, line, call.son.id)
    await call.record(
        "tools.son.bless_line", roles={IncidentRole.ACTOR: call.son.id}, facts={"name": line.name, "reason": args.reason}, kind=ChronicleKind.FATE
    )
    return result(SonResult.LINE_BLESSED, name=line.name, stability=line.stability)


async def curse_line_tool(call: SonCall, args: LineJudgementInput) -> str:
    line = await line_in_world(call.tick, args.line_id, call.son.current_world_id)
    if line is None:
        fail(SonResult.LINE_JUDGEMENT_REFUSED, why="there is no such line in your world")
    await curse_line(call.tick, line, call.son.id)
    await call.record(
        "tools.son.curse_line", roles={IncidentRole.ACTOR: call.son.id}, facts={"name": line.name, "reason": args.reason}, kind=ChronicleKind.FATE
    )
    return result(SonResult.LINE_CURSED, name=line.name, stability=line.stability)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.BLESS_LINE, son, LineJudgementInput, meta, bless_line_tool),
        ToolSpec(SonToolId.CURSE_LINE, son, LineJudgementInput, meta, curse_line_tool),
    ]
