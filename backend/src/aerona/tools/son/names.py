from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.intrigue.names import teach_name
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon
from aerona.tools.son.support import ensure_in_reach, require_essence


class RevealTrueNameInput(ToolInput):
    bearer_id: int
    learner_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def reveal_true_name(call: SonCall, args: RevealTrueNameInput) -> str:
    learner = await require_canon(call.session, args.learner_id)
    await ensure_in_reach(call, learner)
    bearer = await call.session.get(NodeRow, args.bearer_id)
    row = await call.session.get(TrueNameRow, args.bearer_id)
    if bearer is None or row is None:
        fail(SonResult.NO_TRUE_NAME, name=bearer.name if bearer is not None else str(args.bearer_id))
    cost = call.rules.costs.influence
    require_essence(call, cost)
    if not await teach_name(call.tick, row, learner.id):
        fail(SonResult.TRUE_NAME_KNOWN, name=learner.name, bearer=bearer.name)
    call.spend_essence(cost)
    call.target(learner.id)
    await call.record(
        "tools.son.reveal_true_name",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.LEARNER: learner.id, IncidentRole.TARGET: bearer.id},
        facts={"reason": str(args.reason)},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.TRUE_NAME_REVEALED, name=learner.name, bearer=bearer.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.REVEAL_TRUE_NAME,
            AgentKind.SON,
            RevealTrueNameInput,
            ToolMeta(ActionKind.INFLUENCE, son_standard_action, essence_cost=lambda rules: rules.costs.influence),
            reveal_true_name,
        ),
    ]
