from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.governance import OrgStrategy
from aerona.engine.governance.heads import STRATEGY_LOCK, set_strategy
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class SwayOrgInput(ToolInput):
    org_id: int
    strategy: OrgStrategy
    reason: Reason


async def sway_org(call: SonCall, args: SwayOrgInput) -> str:
    org = await living_entity(call.session, args.org_id)
    body = await call.session.get(OrgGovernanceRow, args.org_id)
    if org is None or body is None:
        fail(SonResult.ORG_REFUSED, why="there is no such organisation with a governing body")
    await ensure_in_reach(call, org)
    if held(org.id) or STRATEGY_LOCK in (body.locked or []):
        fail(SonResult.ORG_REFUSED, why="a stronger hand holds its course")
    if body.strategy is args.strategy:
        fail(SonResult.ORG_REFUSED, why=f"{org.name} already follows {spoken(args.strategy)}")
    await set_strategy(call.tick, body, args.strategy, call.son.id, args.reason)
    call.target(org.id)
    return result(SonResult.ORG_SWAYED, org=org.name, strategy=spoken(args.strategy))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.SWAY_ORG, AgentKind.SON, SwayOrgInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), sway_org)]
