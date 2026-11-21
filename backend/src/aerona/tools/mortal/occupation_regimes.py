from typing import Any

from pydantic import Field

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationRegimeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.occupation_regimes import CollaborationFate, CollaborationKind, OccupationMeasure, OccupationRule
from aerona.engine.occupation_regime.book import RegimeTally, locals_of
from aerona.engine.occupation_regime.collaborators import join
from aerona.engine.occupation_regime.measures import impose
from aerona.engine.occupation_regime.rule import set_rule
from aerona.engine.primitives.folk import homes_for
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.monetary import controls


class SetOccupationRuleInput(ToolInput):
    occupation_id: int
    rule: OccupationRule


class CollaborateInput(ToolInput):
    occupation_id: int
    kind: CollaborationKind


class ImposeMeasureInput(ToolInput):
    occupation_id: int
    measure: OccupationMeasure
    strength: int = Field(ge=1, le=PERCENT)


class ExposeCollaboratorInput(ToolInput):
    collaboration_id: int


async def open_regime(call: MortalCall, regime_id: int) -> OccupationRegimeRow:
    regime = await call.session.get(OccupationRegimeRow, regime_id)
    if regime is None or regime.ended_epoch is not None:
        fail(MortalResult.OCCUPATION_REFUSED, why="there is no such occupation still in force")
    if held(regime.region_entity_id) or held(regime.occupier_entity_id):
        fail(MortalResult.OCCUPATION_REFUSED, why="a god holds it as it is")
    return regime


async def lives_under(call: MortalCall, regime: OccupationRegimeRow) -> bool:
    homes = await homes_for(call.session, [entity.id for entity in await locals_of(call.tick, regime)])
    return call.me.location_id in homes


async def ruled_by_me(call: MortalCall, regime_id: int) -> OccupationRegimeRow:
    regime = await open_regime(call, regime_id)
    if not await controls(call, regime.occupier_entity_id):
        fail(MortalResult.OCCUPATION_REFUSED, why="only the ruler of the occupier decides how the occupied land is ruled")
    return regime


async def set_occupation_rule_tool(call: MortalCall, args: SetOccupationRuleInput) -> str:
    regime = await ruled_by_me(call, args.occupation_id)
    if not await set_rule(call.tick, regime, args.rule, RegimeTally(), by=call.me.id):
        fail(MortalResult.OCCUPATION_REFUSED, why=f"it is already under {spoken(args.rule)} rule, or a god holds its rule")
    call.target(regime.region_entity_id)
    return result(MortalResult.OCCUPATION_RULE_SET, rule=spoken(args.rule), tax=regime.tax_pct)


async def collaborate_tool(call: MortalCall, args: CollaborateInput) -> str:
    regime = await open_regime(call, args.occupation_id)
    if not await lives_under(call, regime):
        fail(MortalResult.OCCUPATION_REFUSED, why="only those who live under an occupation can serve it")
    row = await join(call.tick, regime, call.me.id, args.kind, RegimeTally())
    call.target(regime.occupier_entity_id)
    return result(MortalResult.COLLABORATION_BEGUN, kind=spoken(args.kind), reward=row.reward)


async def impose_measure_tool(call: MortalCall, args: ImposeMeasureInput) -> str:
    regime = await ruled_by_me(call, args.occupation_id)
    row = await impose(call.tick, regime, args.measure, args.strength, RegimeTally(), by=call.me.id)
    call.target(regime.region_entity_id)
    return result(MortalResult.OCCUPATION_MEASURE_IMPOSED, measure=spoken(args.measure), strength=row.strength)


async def expose_collaborator_tool(call: MortalCall, args: ExposeCollaboratorInput) -> str:
    row = await call.session.get(CollaborationRow, args.collaboration_id)
    if row is None or row.fate is not CollaborationFate.SERVING:
        fail(MortalResult.OCCUPATION_REFUSED, why="no one serves the occupier under that name")
    regime = await open_regime(call, row.regime_id)
    if row.collaborator_node_id == call.me.id or not await lives_under(call, regime):
        fail(MortalResult.OCCUPATION_REFUSED, why="only those who live under the occupation can expose its servants")
    if held(row.collaborator_node_id) or "exposure" in (row.locked or []):
        fail(MortalResult.OCCUPATION_REFUSED, why="a god holds that one as they are")
    row.exposure = PERCENT
    call.target(row.collaborator_node_id)
    await call.record(
        "occupation.collaborator_exposed",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: row.collaborator_node_id, IncidentRole.SUBJECT: regime.region_entity_id},
        facts={"kind": row.kind},
    )
    return result(MortalResult.COLLABORATOR_EXPOSED, kind=spoken(row.kind))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.SET_OCCUPATION_RULE, AgentKind.MORTAL, SetOccupationRuleInput, act, set_occupation_rule_tool),
        ToolSpec(MortalToolId.COLLABORATE, AgentKind.MORTAL, CollaborateInput, act, collaborate_tool),
        ToolSpec(MortalToolId.IMPOSE_MEASURE, AgentKind.MORTAL, ImposeMeasureInput, act, impose_measure_tool),
        ToolSpec(MortalToolId.EXPOSE_COLLABORATOR, AgentKind.MORTAL, ExposeCollaboratorInput, act, expose_collaborator_tool),
    ]
