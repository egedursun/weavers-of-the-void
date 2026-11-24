from aerona.domain.enums.economy import TradeMode, TradeRouteStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.routes import LIVE_STATUSES, Route, route_locked
from aerona.engine.environment.deep_war import DeepWarTally
from aerona.engine.primitives.deep_paths import cut_below, tell_route_cut, tell_route_reopened

CUTTABLE = LIVE_STATUSES - {TradeRouteStatus.BLOCKADED}


async def keep_deep_routes(ctx: TickContext, routes: list[Route], tally: DeepWarTally) -> None:
    for route in routes:
        if route.profile.mode is not TradeMode.UNDERGROUND:
            continue
        route.cut = await cut_below(ctx, route.entity.id, route.profile.mode, route.cells)
        if route_locked(route, "status"):
            continue
        if route.cut and route.profile.status in CUTTABLE:
            route.profile.status, route.profile.blockaded_by_entity_id = TradeRouteStatus.BLOCKADED, None
            tally.cut += 1
            await tell_route_cut(ctx, route.entity.id, route.cells)
        elif not route.cut and route.profile.status is TradeRouteStatus.BLOCKADED and route.profile.blockaded_by_entity_id is None:
            route.profile.status = TradeRouteStatus.OPEN
            tally.reopened += 1
            await tell_route_reopened(ctx, route.entity.id, route.cells)
