from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.reckoning import ReckoningMeasureRow, ReckoningRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.reckoning import MeasureStage, ReckoningMeasure
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
WEIGHT = 25


class WeighReckoningInput(ToolInput):
    reckoning_id: int
    measure: ReckoningMeasure
    reason: Reason


async def weigh_reckoning(call: SonCall, args: WeighReckoningInput) -> str:
    row = await call.session.get(ReckoningRow, args.reckoning_id)
    realm = await living_entity(call.session, row.polity_entity_id) if row is not None else None
    if row is None or realm is None or row.closed_epoch is not None:
        fail(SonResult.RECKONING_REFUSED, why="there is no such reckoning still open")
    await ensure_in_reach(call, realm)
    if held(realm.id):
        fail(SonResult.RECKONING_REFUSED, why="that realm is held")
    query = select(ReckoningMeasureRow).where(ReckoningMeasureRow.reckoning_id == row.id, ReckoningMeasureRow.measure == args.measure)
    measure = await call.session.scalar(query.limit(1))
    if measure is None:
        measure = ReckoningMeasureRow(
            reckoning_id=row.id, polity_entity_id=row.polity_entity_id, measure=args.measure, strength=0, stage=MeasureStage.PLANNED, locked=[]
        )
        call.session.add(measure)
    if "strength" in (measure.locked or []):
        fail(SonResult.RECKONING_REFUSED, why="that measure is held")
    measure.strength = clamp_int(measure.strength + WEIGHT, 0, PERCENT)
    call.target(realm.id)
    await call.record("reckoning.weighed", roles={IncidentRole.SUBJECT: realm.id}, facts={"measure": args.measure, "strength": measure.strength})
    return result(SonResult.RECKONING_WEIGHED, realm=realm.name, strength=measure.strength)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.WEIGH_RECKONING, AgentKind.SON, WeighReckoningInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), weigh_reckoning)]
