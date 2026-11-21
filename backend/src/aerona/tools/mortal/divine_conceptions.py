from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.divine_conceptions import DivineConceptionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultOfficeRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.divine_conceptions import ConceptionAxis
from aerona.domain.enums.mind import SkillKind
from aerona.engine.divine_conceptions.tend import set_axis, value_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

Stance = Annotated[str, Field(min_length=1, max_length=40)]


class ArgueDoctrineInput(ToolInput):
    faith_id: int
    conception_axis: ConceptionAxis
    stance: Stance


async def argue_doctrine(call: MortalCall, args: ArgueDoctrineInput) -> str:
    row = await call.session.get(DivineConceptionRow, args.faith_id)
    faith = await call.session.get(EntityRow, args.faith_id)
    if row is None or faith is None:
        fail(MortalResult.DOCTRINE_REFUSED, why="that faith has no settled conception of the divine yet")
    office = select(CultOfficeRow.id).where(CultOfficeRow.cult_entity_id == faith.id, CultOfficeRow.holder_entity_id == call.me.id).limit(1)
    if await call.session.scalar(office) is None:
        fail(MortalResult.DOCTRINE_REFUSED, why="only its clergy argue its doctrine")
    value = value_of(args.conception_axis, args.stance)
    if value is None:
        fail(MortalResult.DOCTRINE_REFUSED, why=f"{args.stance} is no way to hold the {spoken(args.conception_axis)} of the divine")
    if held(faith.id) or args.conception_axis.value in row.locked:
        fail(MortalResult.DOCTRINE_REFUSED, why="a god holds that faith unchanged")
    skill = await call.session.scalar(select(SkillRow.level).where(SkillRow.holder_node_id == call.me.id, SkillRow.skill == SkillKind.THEOLOGY).limit(1)) or 0
    call.target(faith.id)
    if not call.tick.rng(f"argue.{faith.id}.{call.me.id}.{call.tick.epoch}").chance(min(PERCENT, skill)):
        return result(MortalResult.DOCTRINE_UNHEARD, faith=faith.name)
    await set_axis(call.tick, row, args.conception_axis, value, by=call.me.id)
    return result(MortalResult.DOCTRINE_ARGUED, faith=faith.name, axis=spoken(args.conception_axis), value=spoken(value))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [ToolSpec(MortalToolId.ARGUE_DOCTRINE, AgentKind.MORTAL, ArgueDoctrineInput, act, argue_doctrine)]
