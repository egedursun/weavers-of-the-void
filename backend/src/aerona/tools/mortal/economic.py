from typing import Any

from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.orders import ExchangeRateRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.orders import AllocationMode, Compensation, DistributionRule, OrderLabour, OwnershipRegime, TransitionKind
from aerona.engine.orders.economy import axes_of, changed_axes, locked_axes, open_transition, order_of, set_order, transition_target
from aerona.engine.orders.economy import begin_transition as proclaim
from aerona.engine.sacred.places import ruler_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.inputs import Reason


class SetEconomicOrderInput(ToolInput):
    polity_id: int
    sector: CommodityKind | None = None
    ownership: OwnershipRegime
    allocation: AllocationMode
    labour: OrderLabour
    distribution: DistributionRule
    reason: Reason


class BeginTransitionInput(ToolInput):
    polity_id: int
    sector: CommodityKind | None = None
    kind: TransitionKind
    compensation: Compensation
    reason: Reason


class ChangeMoneyInput(ToolInput):
    pass


async def ruled_realm(call: MortalCall, polity_id: int, refused: MortalResult) -> EntityRow:
    realm = await call.session.get(EntityRow, polity_id)
    if realm is None or realm.entity_type is not EntityType.POLITY:
        fail(refused, why="there is no such realm")
    if held(realm.id):
        fail(refused, why="that realm is held")
    if await ruler_of(call.session, realm.id) != call.me.id:
        fail(refused, why=f"you do not rule {realm.name}")
    return realm


async def set_economic_order(call: MortalCall, args: SetEconomicOrderInput) -> str:
    realm = await ruled_realm(call, args.polity_id, MortalResult.ORDER_REFUSED)
    axes = {"ownership": args.ownership.value, "allocation": args.allocation.value, "labour": args.labour.value, "distribution": args.distribution.value}
    fast = locked_axes(await order_of(call.session, realm.id, args.sector), axes)
    if fast:
        fail(MortalResult.ORDER_REFUSED, why=f"the {' and '.join(fast)} of {realm.name} is held fast")
    await set_order(call.tick, realm.id, args.sector, axes)
    call.target(realm.id)
    await call.record(
        "tools.mortal.set_economic_order",
        roles={IncidentRole.AUTHORITY: call.me.id, IncidentRole.SUBJECT: realm.id},
        facts={"ownership": args.ownership, "allocation": args.allocation, "labour": args.labour, "distribution": args.distribution, "reason": args.reason},
    )
    return result(MortalResult.ORDER_SET, realm=realm.name, allocation=spoken(args.allocation))


async def begin_transition(call: MortalCall, args: BeginTransitionInput) -> str:
    realm = await ruled_realm(call, args.polity_id, MortalResult.TRANSITION_REFUSED)
    if await open_transition(call.session, realm.id, args.sector) is not None:
        fail(MortalResult.TRANSITION_REFUSED, why=f"a change of the order of {realm.name} is already under way")
    order = await order_of(call.session, realm.id, args.sector)
    wanted = await transition_target(call.session, realm.id, args.kind)
    current = axes_of(order) if order is not None else {}
    if not changed_axes(current, wanted):
        fail(MortalResult.TRANSITION_REFUSED, why=f"the order of {realm.name} is already what that change would make it")
    fast = locked_axes(order, wanted)
    if fast:
        fail(MortalResult.TRANSITION_REFUSED, why=f"the {' and '.join(fast)} of {realm.name} is held fast")
    row = await proclaim(call.tick, realm.id, args.sector, args.kind, args.compensation)
    call.target(realm.id)
    await call.record(
        "tools.mortal.begin_transition",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.AUTHORITY: realm.id},
        facts={"transition": args.kind, "compensation": args.compensation, "sector": args.sector, "reason": args.reason},
    )
    return result(MortalResult.TRANSITION_BEGUN, realm=realm.name, kind=spoken(args.kind), id=row.id)


async def change_money(call: MortalCall, args: ChangeMoneyInput) -> str:
    skill = await call.session.scalar(select(SkillRow.level).where(SkillRow.holder_node_id == call.me.id, SkillRow.skill == SkillKind.ACCOUNTING).limit(1))
    if (skill or 0) < call.tick.rules.exchange_rates.changer_skill:
        fail(MortalResult.CHANGING_REFUSED, why="you lack the accounting to change money")
    if call.me.location_id is None:
        fail(MortalResult.CHANGING_REFUSED, why="you stand at no market")
    if held(call.me.location_id):
        fail(MortalResult.CHANGING_REFUSED, why="this market is held")
    rates = list(await call.session.scalars(select(ExchangeRateRow).where(ExchangeRateRow.market_entity_id == call.me.location_id)))
    taken = [row for row in rates if "changer_node_id" not in row.locked]
    if not taken:
        fail(MortalResult.CHANGING_REFUSED, why="no two coins meet at your market")
    for row in taken:
        row.changer_node_id = call.me.id
    call.target(call.me.location_id)
    await call.record(
        "tools.mortal.change_money",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: call.me.location_id},
        facts={"rates": len(taken)},
        place=call.me.location_id,
    )
    return result(MortalResult.MONEY_CHANGED, rates=len(taken))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.SET_ECONOMIC_ORDER, mortal, SetEconomicOrderInput, meta, set_economic_order),
        ToolSpec(MortalToolId.BEGIN_TRANSITION, mortal, BeginTransitionInput, meta, begin_transition),
        ToolSpec(MortalToolId.CHANGE_MONEY, mortal, ChangeMoneyInput, meta, change_money),
    ]
