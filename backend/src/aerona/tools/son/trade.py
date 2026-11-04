from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.god_lines import Line
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import TradeMode, TradeRouteStatus
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityStatus, EntityType
from aerona.engine.economy.control import open_route
from aerona.engine.economy.route_control import found_by_hand
from aerona.engine.economy.routes import load_routes
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach, require_essence

ROUTE_OPENED = Line("tools.son.trade_route_opened", "{son} laid {route} between {first} and {second}: {reason}")
ROUTE_CLOSED = Line("tools.son.trade_route_closed", "{son} closed {route}; no caravan passes between {first} and {second}: {reason}")


class OpenTradeRouteInput(ToolInput):
    first_id: int
    second_id: int
    mode: TradeMode | None = None
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class CloseTradeRouteInput(ToolInput):
    route_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def open_trade_route(call: SonCall, args: OpenTradeRouteInput) -> str:
    table = call.rules.son_routes
    if args.first_id == args.second_id:
        fail(SonResult.SAME_MARKET)
    ends = []
    for end_id in (args.first_id, args.second_id):
        end = await require_canon(call.session, end_id)
        require_type(end, SOCIETY_TYPES, SonResult.NOT_A_MARKET, name=end.name)
        await ensure_in_reach(call, end)
        ends.append(end)
    first, second = ends
    require_essence(call, table.open_cost)
    pair = frozenset((first.id, second.id))
    known = [route for route in await load_routes(call.tick, live_only=False) if frozenset(route.ends) == pair]
    shut = next((route for route in known if route.profile.status is TradeRouteStatus.CLOSED), None)
    live = next((route for route in known if route.profile.status is not TradeRouteStatus.CLOSED and route.entity.status is EntityStatus.CANON), None)
    if shut is not None:
        entity = await open_route(call.tick, route_id=shut.entity.id, first_id=None, second_id=None)
        template, mode = SonResult.TRADE_ROUTE_REOPENED, shut.profile.mode
    elif live is not None:
        fail(SonResult.TRADE_ROUTE_EXISTS, first=first.name, second=second.name, id=live.entity.id, name=live.entity.name)
    else:
        try:
            route = await found_by_hand(call.tick, first.id, second.id, mode=args.mode, controller_id=None, toll_pct=None)
        except ValidationFailedError:
            fail(SonResult.NO_TRADE_WAY, first=first.name, second=second.name)
        entity, template, mode = route.entity, SonResult.TRADE_ROUTE_OPENED, route.profile.mode
        entity.creator_son_id = call.son.id
    call.spend_essence(table.open_cost)
    call.target(entity.id)
    await call.chronicle(
        ChronicleKind.TRADE,
        ROUTE_OPENED,
        entity_ids=[entity.id, first.id, second.id],
        son=call.son.name,
        route=entity.name,
        first=first.name,
        second=second.name,
        reason=args.reason,
    )
    return result(template, id=entity.id, name=entity.name, mode=mode.value)


async def close_trade_route(call: SonCall, args: CloseTradeRouteInput) -> str:
    table = call.rules.son_routes
    entity = require_type(await require_canon(call.session, args.route_id), {EntityType.TRADE_ROUTE}, SonResult.NOT_A_TRADE_ROUTE)
    await ensure_in_reach(call, entity)
    profile = await call.session.get(TradeRouteProfileRow, entity.id)
    if profile is None:
        fail(SonResult.NOT_A_TRADE_ROUTE)
    if profile.status is TradeRouteStatus.CLOSED:
        fail(SonResult.TRADE_ROUTE_SHUT, id=entity.id, name=entity.name)
    require_essence(call, table.close_cost)
    profile.status = TradeRouteStatus.CLOSED
    profile.closed_by_son_id = call.son.id
    call.spend_essence(table.close_cost)
    call.target(entity.id)
    first, second = await call.session.get_one(type(entity), profile.first_market_id), await call.session.get_one(type(entity), profile.second_market_id)
    await call.chronicle(
        ChronicleKind.TRADE,
        ROUTE_CLOSED,
        entity_ids=[entity.id, first.id, second.id],
        son=call.son.name,
        route=entity.name,
        first=first.name,
        second=second.name,
        reason=args.reason,
    )
    return result(SonResult.TRADE_ROUTE_CLOSED, id=entity.id, name=entity.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(
            SonToolId.OPEN_TRADE_ROUTE,
            son,
            OpenTradeRouteInput,
            ToolMeta(ActionKind.ESTABLISH_TRADE, lambda rules: rules.son_routes.open_ap, essence_cost=lambda rules: rules.son_routes.open_cost),
            open_trade_route,
        ),
        ToolSpec(
            SonToolId.CLOSE_TRADE_ROUTE,
            son,
            CloseTradeRouteInput,
            ToolMeta(ActionKind.OTHER, lambda rules: rules.son_routes.close_ap, essence_cost=lambda rules: rules.son_routes.close_cost),
            close_trade_route,
        ),
    ]
