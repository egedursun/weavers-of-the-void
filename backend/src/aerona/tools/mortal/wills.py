from typing import Annotated, Any

from pydantic import Field

from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.demography import wills
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class MakeWillInput(ToolInput):
    heirs: Annotated[list[int], Field(min_length=1, max_length=12)]
    shares: Annotated[list[int], Field(min_length=1, max_length=12)]


async def make_will(call: MortalCall, args: MakeWillInput) -> str:
    if len(args.heirs) != len(args.shares):
        fail(MortalResult.WILL_REFUSED, why="name one share for each heir")
    try:
        will = await wills.make_will(call.tick, call.me, list(zip(args.heirs, args.shares, strict=True)))
    except ValidationFailedError as error:
        fail(MortalResult.WILL_REFUSED, why=str(error).rstrip(".").lower())
    heirs = [line.heir_node_id for line in await wills.heirs_of_will(call.session, will.id)]
    await call.record("tools.mortal.make_will", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.HEIR: heirs}, facts={"heirs": len(heirs)})
    return result(MortalResult.WILL_MADE, heirs=len(heirs))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.MAKE_WILL, AgentKind.MORTAL, MakeWillInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), make_will)]
