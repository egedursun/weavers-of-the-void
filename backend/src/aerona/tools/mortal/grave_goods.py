from typing import Any

from pydantic import Field

from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.grave_goods import GraveGuard
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.grave_goods.acts import guard_allowed, lay_goods, set_guard
from aerona.engine.grave_goods.robbery import GUARD_STEPS, GraveTally, rob
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.primitives.queries import active_bonds
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

ITEMS_MAX = 6


class PlaceGraveGoodsInput(ToolInput):
    grave_id: int
    item_ids: list[int] = Field(min_length=1, max_length=ITEMS_MAX)


class RobGraveInput(ToolInput):
    grave_id: int


class GuardGraveInput(ToolInput):
    grave_id: int
    guard: GraveGuard


async def grave_here(call: MortalCall, grave_id: int) -> tuple[GraveGoodsRow, EntityRow]:
    row = await call.session.get(GraveGoodsRow, grave_id)
    dead = await call.session.get(EntityRow, row.dead_entity_id) if row is not None else None
    if row is None or dead is None or row.robbed_epoch is not None or row.found_epoch is not None:
        fail(MortalResult.GRAVE_REFUSED, why="there is no such grave still holding its goods")
    if dead.location_id != call.me.location_id:
        fail(MortalResult.GRAVE_REFUSED, why="that grave lies elsewhere")
    if held(dead.id):
        fail(MortalResult.GRAVE_REFUSED, why="a god holds that grave as it is")
    return row, dead


async def place_grave_goods_tool(call: MortalCall, args: PlaceGraveGoodsInput) -> str:
    row, dead = await grave_here(call, args.grave_id)
    owned = {bond.target_node_id for bond in await active_bonds(call.session, [BondKind.OWNS], sources=[call.me.id])}
    laid = [item for item in [await call.session.get(EntityRow, item_id) for item_id in args.item_ids] if item is not None and item.id in owned]
    if len(laid) != len(set(args.item_ids)):
        fail(MortalResult.GRAVE_REFUSED, why="you can lay only what is yours")
    await lay_goods(call.tick, row, dead, laid)
    call.target(dead.id)
    return result(MortalResult.GOODS_LAID, dead=dead.name, items=", ".join(item.name for item in laid))


async def rob_grave_tool(call: MortalCall, args: RobGraveInput) -> str:
    row, dead = await grave_here(call, args.grave_id)
    if call.me.id in await close_kin_of(call.session, dead.id):
        fail(MortalResult.GRAVE_REFUSED, why="you will not rob the grave of your own kin")
    call.target(dead.id)
    taken = await rob(call.tick, row, call.me, GraveTally())
    return result(MortalResult.GRAVE_ROBBED if taken else MortalResult.ROBBER_CAUGHT, dead=dead.name)


async def guard_grave_tool(call: MortalCall, args: GuardGraveInput) -> str:
    row, dead = await grave_here(call, args.grave_id)
    if "guard" in (row.locked or []):
        fail(MortalResult.GRAVE_REFUSED, why="a god holds that grave's guard as it is")
    if not await guard_allowed(call.tick, row, args.guard, dead.location_id):
        fail(MortalResult.GRAVE_REFUSED, why=f"the laws of this land do not let a grave be kept {spoken(args.guard)}")
    cost = GUARD_STEPS[args.guard] * call.tick.rules.grave_goods.guard_cost
    if await points_of(call.session, call.me) < cost:
        fail(MortalResult.GRAVE_REFUSED, why=f"keeping it {spoken(args.guard)} costs {cost} of wealth you lack")
    await shift_points(call.session, call.me, -cost)
    await set_guard(call.tick, row, args.guard, call.me.id, dead.location_id)
    call.target(dead.id)
    return result(MortalResult.GRAVE_GUARDED, dead=dead.name, guard=spoken(args.guard))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.PLACE_GRAVE_GOODS, AgentKind.MORTAL, PlaceGraveGoodsInput, act, place_grave_goods_tool),
        ToolSpec(MortalToolId.ROB_GRAVE, AgentKind.MORTAL, RobGraveInput, act, rob_grave_tool),
        ToolSpec(MortalToolId.GUARD_GRAVE, AgentKind.MORTAL, GuardGraveInput, act, guard_grave_tool),
    ]
