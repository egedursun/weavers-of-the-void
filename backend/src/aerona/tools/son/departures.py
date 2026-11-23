from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.departures.leave import leave
from aerona.engine.departures.weigh import seats, terms_for, weigh
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class CallToStepAsideInput(ToolInput):
    holder_id: int
    reason: Reason


async def call_to_step_aside(call: SonCall, args: CallToStepAsideInput) -> str:
    holder = await living_entity(call.session, args.holder_id)
    if holder is None:
        fail(SonResult.DEPARTURE_REFUSED, why="there is no such living holder")
    await ensure_in_reach(call, holder)
    found = [seat for seat in await seats(call.tick) if seat.holder.id == holder.id]
    if not found:
        fail(SonResult.DEPARTURE_REFUSED, why=f"{holder.name} holds no office to step aside from")
    if held(holder.id):
        fail(SonResult.DEPARTURE_REFUSED, why="they are held as they are")
    call.target(holder.id)
    if not call.tick.rng(f"departures.call.{holder.id}.{call.tick.epoch}").chance(call.tick.rules.departures.call_heed_pct):
        await call.record("office.call_refused", roles={IncidentRole.ACTOR: holder.id}, facts={"why": args.reason})
        return result(SonResult.STEP_ASIDE_REFUSED, holder=holder.name)
    seat = found[0]
    _weight, kind, _customary = await weigh(call.tick, seat)
    row = await leave(call.tick, seat, kind, heir=None, conditions=terms_for(kind), why=args.reason)
    return result(SonResult.STEPPED_ASIDE, holder=holder.name, kind=spoken(row.kind))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(SonToolId.CALL_TO_STEP_ASIDE, AgentKind.SON, CallToStepAsideInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), call_to_step_aside)
    ]
