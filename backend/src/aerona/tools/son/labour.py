from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.demography import Job
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.labour.bodies import body_covering, trade_workers
from aerona.engine.labour.founding import form_for, found_body
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
STIR_FACTOR = 2


class StirLabourInput(ToolInput):
    settlement_id: int
    trade: Job
    reason: Reason


async def stir_labour(call: SonCall, args: StirLabourInput) -> str:
    town = await living_entity(call.session, args.settlement_id)
    if town is None:
        fail(SonResult.LABOUR_REFUSED, why="there is no such town")
    await ensure_in_reach(call, town)
    if held(town.id):
        fail(SonResult.LABOUR_REFUSED, why="that town is held")
    if not await trade_workers(call.session, town.id, [args.trade]):
        fail(SonResult.LABOUR_REFUSED, why=f"no one works {spoken(args.trade)} at {town.name}")
    body = await body_covering(call.session, town.id, args.trade)
    call.target(town.id)
    if body is None:
        made = await found_body(call.tick, town, [args.trade], await form_for(call.tick, town.id, args.trade))
        faction = await call.session.get(EntityRow, made.faction_node_id)
        return result(SonResult.LABOUR_STIRRED, town=town.name, trade=spoken(args.trade), outcome=f"they founded {faction.name if faction else 'a body'}")
    if held(body.faction_node_id) or "solidarity" in (body.locked or []):
        fail(SonResult.LABOUR_REFUSED, why="that body is held as it is")
    gain = call.tick.rules.labour.solidarity_won * STIR_FACTOR
    body.solidarity = clamp_int(body.solidarity + gain, 0, PERCENT)
    await call.record(
        "labour.body_stirred",
        roles={IncidentRole.SUBJECT: body.faction_node_id, IncidentRole.PLACE: town.id},
        facts={"trade": args.trade, "solidarity": body.solidarity},
        place=town.id,
    )
    return result(SonResult.LABOUR_STIRRED, town=town.name, trade=spoken(args.trade), outcome=f"their solidarity rose to {body.solidarity}")


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.STIR_LABOUR, AgentKind.SON, StirLabourInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), stir_labour)]
