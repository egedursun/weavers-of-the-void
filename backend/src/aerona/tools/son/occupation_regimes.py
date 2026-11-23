from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.occupation_regimes import OccupationRegimeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.occupation_regimes import OccupationMeasure, OccupationRule
from aerona.engine.occupation_regime.book import RegimeTally
from aerona.engine.occupation_regime.measures import impose
from aerona.engine.occupation_regime.rule import set_rule
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
SWAYED_STRENGTH = 50


class SwayOccupationInput(ToolInput):
    occupation_id: int
    rule_or_measure: OccupationRule | OccupationMeasure
    reason: Reason


async def sway_occupation(call: SonCall, args: SwayOccupationInput) -> str:
    regime = await call.session.get(OccupationRegimeRow, args.occupation_id)
    region = await call.session.get(EntityRow, regime.region_entity_id) if regime is not None else None
    if regime is None or region is None or regime.ended_epoch is not None:
        fail(SonResult.OCCUPATION_REFUSED, why="there is no such occupation still in force")
    await ensure_in_reach(call, region)
    if held(regime.region_entity_id) or held(regime.occupier_entity_id):
        fail(SonResult.OCCUPATION_REFUSED, why="that occupation is held as it is")
    choice = args.rule_or_measure
    if isinstance(choice, OccupationRule):
        if not await set_rule(call.tick, regime, choice, RegimeTally(), by=call.son.id):
            fail(SonResult.OCCUPATION_REFUSED, why=f"it is already under {spoken(choice)} rule, or its rule is held")
    else:
        await impose(call.tick, regime, choice, SWAYED_STRENGTH, RegimeTally(), by=call.son.id)
    call.target(region.id)
    return result(SonResult.OCCUPATION_SWAYED, region=region.name, choice=spoken(choice))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.SWAY_OCCUPATION, AgentKind.SON, SwayOccupationInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), sway_occupation)]
