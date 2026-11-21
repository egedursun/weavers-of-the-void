from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.grave_goods import GraveGuard
from aerona.engine.grave_goods.acts import guard_allowed, set_guard
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class KeepTheDeadInput(ToolInput):
    grave_id: int
    guard: GraveGuard
    reason: Reason


async def keep_the_dead(call: SonCall, args: KeepTheDeadInput) -> str:
    row = await call.session.get(GraveGoodsRow, args.grave_id)
    dead = await call.session.get(EntityRow, row.dead_entity_id) if row is not None else None
    if row is None or dead is None:
        fail(SonResult.DEAD_REFUSED, why="there is no such grave")
    await ensure_in_reach(call, dead)
    if held(dead.id) or "guard" in (row.locked or []):
        fail(SonResult.DEAD_REFUSED, why="a stronger hand holds that grave as it is")
    if not await guard_allowed(call.tick, row, args.guard, dead.location_id):
        fail(SonResult.DEAD_REFUSED, why=f"the laws of that land do not let a grave be kept {spoken(args.guard)}")
    await set_guard(call.tick, row, args.guard, None, dead.location_id)
    call.target(dead.id)
    return result(SonResult.DEAD_KEPT, dead=dead.name, guard=spoken(args.guard))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.KEEP_THE_DEAD, AgentKind.SON, KeepTheDeadInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), keep_the_dead)]
