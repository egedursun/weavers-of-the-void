from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.lifecycle.end_control import wake_now
from aerona.engine.lifecycle.ends import KIND_OF_TYPE
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class WakeLoreInput(ToolInput):
    lore_id: int
    reason: Reason


async def wake_lore(call: SonCall, args: WakeLoreInput) -> str:
    lore = await living_entity(call.session, args.lore_id)
    if lore is None or lore.entity_type not in KIND_OF_TYPE:
        fail(SonResult.WAKE_REFUSED, why="there is no such ideology, theory or rite")
    await ensure_in_reach(call, lore)
    if held(lore.id):
        fail(SonResult.WAKE_REFUSED, why="it is held")
    cost = call.rules.lifecycle_ends.son_cost
    require_essence(call, cost)
    try:
        row = await wake_now(call.tick, lore.id)
    except ValidationFailedError as error:
        fail(SonResult.WAKE_REFUSED, why=str(error).rstrip("."))
    call.spend_essence(cost)
    call.target(lore.id)
    await call.record(
        "tools.son.wake_lore",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: lore.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.LORE_WOKEN, lore=lore.name, state=spoken(row.state))


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.WAKE_LORE, AgentKind.SON, WakeLoreInput, meta, wake_lore)]
