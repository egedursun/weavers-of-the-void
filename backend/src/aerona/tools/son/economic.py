from typing import Annotated, Any, Literal

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.orders import EconomicOrderRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.orders.economy import AXIS_ENUMS, axes_of, set_order
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class MoveEconomicOrderInput(ToolInput):
    polity_id: int
    axis: Literal["ownership", "allocation", "labour", "distribution"]
    value: str
    reason: Reason


async def move_economic_order(call: SonCall, args: MoveEconomicOrderInput) -> str:
    realm = await call.session.get(EntityRow, args.polity_id)
    if realm is None or realm.entity_type is not EntityType.POLITY:
        fail(SonResult.ORDER_MOVE_REFUSED, why="there is no such realm")
    await ensure_in_reach(call, realm)
    if held(realm.id):
        fail(SonResult.ORDER_MOVE_REFUSED, why="a stronger hand holds that realm")
    allowed = [item.value for item in AXIS_ENUMS[args.axis]]
    if args.value not in allowed:
        fail(SonResult.ORDER_MOVE_REFUSED, why=f"{args.axis} may be {', '.join(allowed)}")
    order = await call.session.scalar(select(EconomicOrderRow).where(EconomicOrderRow.polity_entity_id == realm.id, EconomicOrderRow.sector.is_(None)).limit(1))
    if order is not None and args.axis in order.locked:
        fail(SonResult.ORDER_MOVE_REFUSED, why=f"the {args.axis} of {realm.name} is held fast")
    axes = {**(axes_of(order) if order is not None else {}), args.axis: args.value}
    await set_order(call.tick, realm.id, None, axes)
    call.target(realm.id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.MOVE_ECONOMIC_ORDER, entity_ids=[realm.id], son=call.son.name, realm=realm.name, reason=args.reason)
    return result(SonResult.ORDER_MOVED, realm=realm.name, axis=args.axis, value=args.value.replace("_", " "))


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.MOVE_ECONOMIC_ORDER, AgentKind.SON, MoveEconomicOrderInput, meta, move_economic_order)]
