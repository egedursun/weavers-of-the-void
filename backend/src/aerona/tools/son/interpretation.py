from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interpretation import InterpretationRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.interpretation import InterpretationFault
from aerona.domain.enums.modifier import IncidentRole
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class ConfuseTonguesInput(ToolInput):
    event_id: int
    reason: Reason


async def confuse_tongues(call: SonCall, args: ConfuseTonguesInput) -> str:
    row = await call.session.get(InterpretationRow, args.event_id)
    party = await call.session.get(EntityRow, row.first_party_id) if row is not None else None
    if row is None or party is None:
        fail(SonResult.TONGUES_REFUSED, why="there is no such exchange between tongues")
    await ensure_in_reach(call, party)
    if held(row.first_party_id) or held(row.second_party_id) or "fault" in (row.locked or []):
        fail(SonResult.TONGUES_REFUSED, why="that exchange is held as it is")
    row.fault, row.fidelity, row.found, row.favoured_party_id = InterpretationFault.LOST_MEANING, row.fidelity // 2, False, None
    call.target(row.second_party_id)
    await call.record("tongue.confused", roles={IncidentRole.SUBJECT: row.first_party_id, IncidentRole.TARGET: row.second_party_id}, facts={"event": row.event})
    return result(SonResult.TONGUES_CONFUSED, event=spoken(row.event))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.CONFUSE_TONGUES, AgentKind.SON, ConfuseTonguesInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), confuse_tongues)]
