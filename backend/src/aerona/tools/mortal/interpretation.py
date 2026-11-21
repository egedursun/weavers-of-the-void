from typing import Any

from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.interpretation import InterpretationRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.interpretation import InterpretationFault
from aerona.domain.enums.mind import SkillKind
from aerona.engine.interpretation.work import side_of, told
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class InterpretInput(ToolInput):
    event_id: int
    slant: bool = False


async def interpret_tool(call: MortalCall, args: InterpretInput) -> str:
    row = await call.session.get(InterpretationRow, args.event_id)
    if row is None or row.found:
        fail(MortalResult.INTERPRETING_REFUSED, why="there is no such exchange still to carry between tongues")
    if held(row.first_party_id) or held(row.second_party_id) or "fault" in (row.locked or []):
        fail(MortalResult.INTERPRETING_REFUSED, why="a god holds that exchange as it is")
    skill = await call.session.scalar(select(SkillRow.level).where(SkillRow.holder_node_id == call.me.id, SkillRow.skill == SkillKind.LANGUAGES).limit(1))
    if skill is None or skill < call.tick.rules.interpreters.interpreter_skill:
        fail(MortalResult.INTERPRETING_REFUSED, why="you lack the skill in tongues to carry it")
    side = await side_of(call.tick, call.me.id, row.first_party_id, row.second_party_id)
    if args.slant and side is None:
        fail(MortalResult.INTERPRETING_REFUSED, why="you belong to neither side, so have none to slant it toward")
    row.interpreter_node_id, row.fidelity = call.me.id, skill
    row.fault, row.favoured_party_id = (InterpretationFault.SLANTED, side) if args.slant else (InterpretationFault.NONE, None)
    await told(call.tick, row)
    call.target(row.second_party_id)
    return result(MortalResult.INTERPRETED, event=spoken(row.event), rendering="slanted toward your side" if args.slant else "faithfully")


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.INTERPRET, AgentKind.MORTAL, InterpretInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), interpret_tool)]
