from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.leader_cults import LeaderCultRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.leader_cults import CultFate, CultInstrument
from aerona.engine.leader_cults.cults import CultTally, add_instrument, begin, may_lead, realm_ruled_by, tear_down
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.monetary import controls

INSTRUMENTS_MAX = 8


class PromoteCultInput(ToolInput):
    leader_id: int
    instruments: list[CultInstrument] = Field(min_length=1, max_length=INSTRUMENTS_MAX)


class TearDownCultInput(ToolInput):
    cult_id: int


async def serves(call: MortalCall, realm: int | None) -> bool:
    if realm is None:
        return False
    office = select(OfficeRow.id).where(OfficeRow.polity_entity_id == realm, OfficeRow.holder_entity_id == call.me.id).limit(1)
    home = (
        select(PolityMemberRow.member_entity_id)
        .where(PolityMemberRow.polity_entity_id == realm, PolityMemberRow.member_entity_id == call.me.location_id)
        .limit(1)
    )
    return await call.session.scalar(office) is not None or await call.session.scalar(home) is not None


async def promote_cult_tool(call: MortalCall, args: PromoteCultInput) -> str:
    leader = await may_lead(call.session, args.leader_id)
    if leader is None:
        fail(MortalResult.CULT_REFUSED, why="a cult is raised to a living mortal or made mind, never to a god")
    realm = await realm_ruled_by(call.session, leader.id)
    if leader.id != call.me.id and not await serves(call, realm):
        fail(MortalResult.CULT_REFUSED, why="you promote the cult of yourself or of the ruler of your realm")
    if held(leader.id) or (realm is not None and held(realm)):
        fail(MortalResult.CULT_REFUSED, why="a god holds it as it is")
    tally = CultTally()
    cult = await begin(call.tick, leader, [call.me.id], tally)
    if call.me.id not in (cult.promoters or []):
        cult.promoters = sorted({*(cult.promoters or []), call.me.id})
    added = [instrument for instrument in dict.fromkeys(args.instruments) if await add_instrument(call.tick, cult, instrument, tally)]
    call.target(leader.id)
    return result(MortalResult.CULT_PROMOTED, leader=leader.name, added=", ".join(spoken(item) for item in added) or "nothing new", intensity=cult.intensity)


async def tear_down_cult_tool(call: MortalCall, args: TearDownCultInput) -> str:
    cult = await call.session.get(LeaderCultRow, args.cult_id)
    if cult is None or cult.fate is not CultFate.LIVING:
        fail(MortalResult.CULT_REFUSED, why="there is no such living cult")
    if cult.polity_entity_id is None or not await controls(call, cult.polity_entity_id):
        fail(MortalResult.CULT_REFUSED, why="only the ruler of the realm tears a cult down")
    if held(cult.leader_node_id) or "fate" in (cult.locked or []):
        fail(MortalResult.CULT_REFUSED, why="a god holds that cult as it is")
    await tear_down(call.tick, cult, CultTally())
    call.target(cult.leader_node_id)
    return result(MortalResult.CULT_TORN_DOWN, cult=cult.id)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.PROMOTE_CULT, AgentKind.MORTAL, PromoteCultInput, act, promote_cult_tool),
        ToolSpec(MortalToolId.TEAR_DOWN_CULT, AgentKind.MORTAL, TearDownCultInput, act, tear_down_cult_tool),
    ]
