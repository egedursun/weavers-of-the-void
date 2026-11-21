from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.referendums import ReferendumRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.referendums import ReferendumResult, VoteSide
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
SWAY = 15
SIDE_SIGN = {VoteSide.YES: 1, VoteSide.NO: -1}


class SwayVoteInput(ToolInput):
    referendum_id: int
    side: VoteSide
    reason: Reason


async def sway_vote(call: SonCall, args: SwayVoteInput) -> str:
    row = await call.session.get(ReferendumRow, args.referendum_id)
    holder = await living_entity(call.session, row.holder_node_id) if row is not None else None
    if row is None or holder is None or row.result is not ReferendumResult.PENDING:
        fail(SonResult.VOTE_REFUSED, why="there is no such vote still to be held")
    await ensure_in_reach(call, holder)
    if held(holder.id) or "yes_pct" in (row.locked or []):
        fail(SonResult.VOTE_REFUSED, why="a stronger hand holds that vote")
    row.yes_pct = clamp_int(row.yes_pct + SWAY * SIDE_SIGN[args.side], 0, PERCENT)
    call.target(holder.id)
    await call.record("vote.swayed", roles={IncidentRole.SUBJECT: holder.id}, facts={"side": args.side, "yes": row.yes_pct})
    return result(SonResult.VOTE_SWAYED, holder=holder.name, yes=row.yes_pct)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.SWAY_VOTE, AgentKind.SON, SwayVoteInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), sway_vote)]
