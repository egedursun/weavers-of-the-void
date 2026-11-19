from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.interconnect import IncidentParticipantRow
from aerona.db.tables.standing import ProfessionOfValueRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.queries import living_entity
from aerona.engine.standing.hypocrisy import expose
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

EVIDENCE_MAX = 5


class ExposeHypocrisyInput(ToolInput):
    target_id: int
    value_axis: ValueAxis
    evidence_incident_ids: list[int] = Field(default_factory=list, max_length=EVIDENCE_MAX)


async def expose_hypocrisy(call: MortalCall, args: ExposeHypocrisyInput) -> str:
    target = await living_entity(call.session, args.target_id)
    if target is None or target.id == call.me.id:
        fail(MortalResult.HYPOCRISY_REFUSED, why="name another who lives")
    row = await call.session.scalar(
        select(ProfessionOfValueRow).where(ProfessionOfValueRow.holder_node_id == target.id, ProfessionOfValueRow.axis == args.value_axis).limit(1)
    )
    if row is None:
        fail(MortalResult.HYPOCRISY_REFUSED, why=f"{target.name} does not profess {spoken(args.value_axis)}")
    if held(target.id) or "exposed" in row.locked:
        fail(MortalResult.HYPOCRISY_REFUSED, why="a god holds their name as it is")
    if row.exposed:
        fail(MortalResult.HYPOCRISY_REFUSED, why="it is known already")
    if args.evidence_incident_ids:
        shown = await call.session.scalars(
            select(IncidentParticipantRow.incident_id).where(
                IncidentParticipantRow.incident_id.in_(args.evidence_incident_ids), IncidentParticipantRow.node_id == target.id
            )
        )
        if not set(shown):
            fail(MortalResult.HYPOCRISY_REFUSED, why="none of those happenings involve them")
    if row.gap < call.rules.standing.hypocrisy_gap_threshold:
        fail(MortalResult.HYPOCRISY_REFUSED, why=f"{target.name} does not act far enough against {spoken(args.value_axis)} for it to stick")
    await expose(call.tick, row, call.me.id)
    call.target(target.id)
    await call.record(
        "tools.mortal.expose_hypocrisy", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: target.id}, facts={"axis": args.value_axis, "gap": row.gap}
    )
    return result(MortalResult.HYPOCRISY_EXPOSED, name=target.name, axis=spoken(args.value_axis), gap=row.gap)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [ToolSpec(MortalToolId.EXPOSE_HYPOCRISY, AgentKind.MORTAL, ExposeHypocrisyInput, meta, expose_hypocrisy)]
