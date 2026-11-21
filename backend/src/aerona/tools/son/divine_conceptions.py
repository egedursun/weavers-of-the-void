from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.divine_conceptions import DivineConceptionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.divine_conceptions import ConceptionAxis
from aerona.domain.enums.entity import EntityType
from aerona.engine.divine_conceptions.conception import conceive
from aerona.engine.divine_conceptions.tend import set_axis, value_of
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
Stance = Annotated[str, Field(min_length=1, max_length=40)]


class RevealNatureInput(ToolInput):
    faith_id: int
    axis: ConceptionAxis
    stance: Stance
    reason: Reason


async def reveal_nature(call: SonCall, args: RevealNatureInput) -> str:
    faith = await call.session.get(EntityRow, args.faith_id)
    if faith is None or faith.entity_type is not EntityType.CULT:
        fail(SonResult.CONCEPTION_REFUSED, why="that is no faith")
    await ensure_in_reach(call, faith)
    value = value_of(args.axis, args.stance)
    if value is None:
        fail(SonResult.CONCEPTION_REFUSED, why=f"{args.stance} is no way to hold the {spoken(args.axis)} of the divine")
    row = await call.session.get(DivineConceptionRow, faith.id) or await conceive(call.tick, faith)
    if held(faith.id) or args.axis.value in row.locked:
        fail(SonResult.CONCEPTION_REFUSED, why="a stronger hand holds that faith unchanged")
    await set_axis(call.tick, row, args.axis, value, by=call.son.id)
    call.target(faith.id)
    return result(SonResult.NATURE_REVEALED, faith=faith.name, axis=spoken(args.axis), value=spoken(value))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.REVEAL_NATURE, AgentKind.SON, RevealNatureInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), reveal_nature)]
