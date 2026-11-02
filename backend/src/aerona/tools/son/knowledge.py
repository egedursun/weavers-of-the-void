from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.gods.progress import power_ceiling
from aerona.engine.phases.knowledge_levels import shift_level
from aerona.engine.primitives.knowledge import knowledge_level
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, grant


class AdvanceInput(ToolInput):
    knowledge_id: int
    how: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def advance_knowledge(call: SonCall, args: AdvanceInput) -> str:
    table = call.rules.knowledge
    knowledge = await require_canon(call.session, args.knowledge_id)
    require_type(knowledge, {EntityType.KNOWLEDGE}, SonResult.NOT_KNOWLEDGE)
    await ensure_in_reach(call, knowledge)
    ceiling = min(table.level_cap, power_ceiling(call.rules, call.son) * table.son_level_per_power)
    if knowledge_level(call.rules, knowledge) >= ceiling:
        fail(SonResult.KNOWLEDGE_CEILING, name=knowledge.name, ceiling=ceiling)
    if call.son.essence < table.son_advance_cost:
        fail(SonResult.TEACH_ESSENCE, cost=table.son_advance_cost)
    level = shift_level(call.rules, knowledge, 1)
    if level is None:
        fail(SonResult.KNOWLEDGE_CEILING, name=knowledge.name, ceiling=table.level_cap)
    call.spend_essence(table.son_advance_cost)
    call.target(knowledge.id)
    gained = await grant(call, call.son, call.rules.son_tools.knowledge_xp, call.rules.son_tools.knowledge_renown)
    await call.chronicle(
        ChronicleKind.KNOWLEDGE, lines.ADVANCE_KNOWLEDGE, entity_ids=[knowledge.id], son=call.son.name, knowledge=knowledge.name, level=level, how=args.how
    )
    return result(SonResult.KNOWLEDGE_ADVANCED, name=knowledge.name, level=level, gained=gained)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.ADVANCE_KNOWLEDGE,
            AgentKind.SON,
            AdvanceInput,
            ToolMeta(
                ActionKind.ADVANCE_KNOWLEDGE,
                son_standard_action,
                essence_cost=lambda rules: rules.knowledge.son_advance_cost,
                rarity_gate=gate(Gate.INFLUENCE_TOOLS),
            ),
            advance_knowledge,
        )
    ]
