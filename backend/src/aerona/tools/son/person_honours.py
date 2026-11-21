from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.honours import HonourKindRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.honours import HonourPrivilege
from aerona.engine.honours.persons import HonourTally, confer, holds
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class HonourServantInput(ToolInput):
    holder_id: int
    reason: Reason


async def own_honour(call: SonCall) -> HonourKindRow:
    kind = await call.session.scalar(
        select(HonourKindRow).where(HonourKindRow.conferrer_node_id == call.son.id).order_by(HonourKindRow.rank, HonourKindRow.id).limit(1)
    )
    if kind is None:
        kind = HonourKindRow(
            conferrer_node_id=call.son.id,
            name=f"Favour of {call.son.name}",
            rank=1,
            privileges=[HonourPrivilege.PRECEDENCE.value],
            founded_epoch=call.tick.epoch,
            locked=[],
        )
        call.session.add(kind)
        await call.session.flush()
    return kind


async def honour_servant(call: SonCall, args: HonourServantInput) -> str:
    holder = await call.session.get(EntityRow, args.holder_id)
    if holder is None or holder.status is not EntityStatus.CANON:
        fail(SonResult.HONOUR_REFUSED, why="there is no such living servant")
    await ensure_in_reach(call, holder)
    kind = await own_honour(call)
    if held(holder.id) or await holds(call.session, holder.id, kind.id):
        fail(SonResult.HONOUR_REFUSED, why="they hold your favour already, or a stronger hand holds them")
    await confer(call.tick, kind, holder, tally=HonourTally(), by=call.son.id)
    call.target(holder.id)
    return result(SonResult.SERVANT_HONOURED, holder=holder.name, honour=kind.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.HONOUR_SERVANT, AgentKind.SON, HonourServantInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), honour_servant)]
