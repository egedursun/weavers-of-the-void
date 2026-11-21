from typing import Any

from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.households import HouseholdMemberRow
from aerona.db.tables.kin_dynamics import KinDisowningRow, KinDynamicRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.kin_dynamics import DisownReason
from aerona.engine.kin_dynamics.acts import disown, favour, reconcile
from aerona.engine.kin_dynamics.book import KinTally, children_of, dynamic_of
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class FavourChildInput(ToolInput):
    child_id: int


class DisownInput(ToolInput):
    member_id: int
    reason: DisownReason


class ReconcileKinInput(ToolInput):
    member_id: int


async def my_dynamic(call: MortalCall) -> KinDynamicRow:
    house = await call.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == call.me.id).limit(1))
    if house is not None:
        return await dynamic_of(call.tick, house=house)
    household = await call.session.scalar(select(HouseholdMemberRow.household_id).where(HouseholdMemberRow.member_node_id == call.me.id).limit(1))
    if household is None:
        fail(MortalResult.FAMILY_REFUSED, why="you belong to no house or household")
    return await dynamic_of(call.tick, household=household)


async def my_child(call: MortalCall, child_id: int) -> int:
    if child_id not in await children_of(call.session, call.me.id) and not await heads_house_of(call, child_id):
        fail(MortalResult.FAMILY_REFUSED, why="that one is not your child, nor of the house you head")
    if held(child_id):
        fail(MortalResult.FAMILY_REFUSED, why="a god holds that one as they are")
    return child_id


async def heads_house_of(call: MortalCall, member_id: int) -> bool:
    houses = select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == member_id)
    query = select(HouseProfileRow.house_entity_id).where(HouseProfileRow.head_entity_id == call.me.id, HouseProfileRow.house_entity_id.in_(houses))
    return await call.session.scalar(query.limit(1)) is not None


async def favour_child_tool(call: MortalCall, args: FavourChildInput) -> str:
    child = await my_child(call, args.child_id)
    row = await favour(call.tick, await my_dynamic(call), call.me.id, child, KinTally())
    named = await living_entity(call.session, child)
    call.target(child)
    return result(MortalResult.CHILD_FAVOURED, child=named.name if named is not None else "the child", strength=row.strength)


async def disown_tool(call: MortalCall, args: DisownInput) -> str:
    member = await living_entity(call.session, await my_child(call, args.member_id))
    if member is None:
        fail(MortalResult.FAMILY_REFUSED, why="there is no such living kin")
    await disown(call.tick, await my_dynamic(call), call.me.id, member, args.reason, tally=KinTally())
    call.target(member.id)
    return result(MortalResult.KIN_DISOWNED, member=member.name, reason=spoken(args.reason))


async def reconcile_kin_tool(call: MortalCall, args: ReconcileKinInput) -> str:
    query = select(KinDisowningRow).where(
        KinDisowningRow.disowner_node_id == call.me.id, KinDisowningRow.disowned_node_id == args.member_id, KinDisowningRow.reconciled_epoch.is_(None)
    )
    row = await call.session.scalar(query.limit(1))
    if row is None or held(args.member_id) or not await reconcile(call.tick, row, KinTally()):
        fail(MortalResult.FAMILY_REFUSED, why="you have cast no such one out, or it cannot be undone")
    member = await living_entity(call.session, args.member_id)
    call.target(args.member_id)
    return result(MortalResult.KIN_RECONCILED, member=member.name if member is not None else "them")


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.FAVOUR_CHILD, AgentKind.MORTAL, FavourChildInput, act, favour_child_tool),
        ToolSpec(MortalToolId.DISOWN, AgentKind.MORTAL, DisownInput, act, disown_tool),
        ToolSpec(MortalToolId.RECONCILE_KIN, AgentKind.MORTAL, ReconcileKinInput, act, reconcile_kin_tool),
    ]
