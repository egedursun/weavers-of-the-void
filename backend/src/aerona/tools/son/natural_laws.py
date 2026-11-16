from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.law_grammar import Grammar
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.law_grammar import LawCondition, LawOperator
from aerona.engine.divine.law_grammar import grammar_of, set_grammar
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class NaturalLawInput(ToolInput):
    law_id: int
    operator: LawOperator
    value: int = Field(default=100, ge=0, le=1000)
    condition: LawCondition = LawCondition.ALWAYS
    reason: Reason


async def set_natural_law(call: SonCall, args: NaturalLawInput) -> str:
    law = await living_entity(call.session, args.law_id)
    if law is None or law.entity_type is not EntityType.NATURAL_LAW:
        fail(SonResult.LAW_REFUSED, why="there is no such law")
    await ensure_in_reach(call, law)
    row = await call.session.get(NaturalLawProfileRow, law.id)
    current = grammar_of(row) if row is not None else None
    if current is None:
        fail(SonResult.LAW_REFUSED, why="that law has no working to reshape yet")
    if row is not None and row.author_node_id != call.son.id:
        cost = call.rules.natural_laws.reshape_essence
        if call.son.essence < cost:
            fail(SonResult.LAW_REFUSED, why="reshaping another's law costs more essence than you hold")
        call.son.essence -= cost
        row.author_node_id = call.son.id
    try:
        await set_grammar(call.tick, law, Grammar(current.target, args.operator, current.key, args.value), args.condition, None, hold=False)
    except ValidationFailedError as error:
        fail(SonResult.LAW_REFUSED, why=str(error).rstrip("."))
    call.target(law.id)
    await call.chronicle(ChronicleKind.COSMIC_LAW, lines.SET_NATURAL_LAW, entity_ids=[law.id], son=call.son.name, name=law.name, reason=args.reason)
    return result(SonResult.LAW_SET, name=law.name, operator=args.operator.value.replace("_", " "), value=args.value)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.SET_NATURAL_LAW, AgentKind.SON, NaturalLawInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), set_natural_law)]
