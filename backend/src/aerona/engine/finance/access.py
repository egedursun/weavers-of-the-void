from collections import defaultdict

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import CommunityIndustryRow
from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.db.write_guard import unheld
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.routes import LIVE_STATUSES
from aerona.engine.industry.energy import industry_row
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules


async def route_dangers(ctx: TickContext) -> dict[int, list[tuple[int, int]]]:
    dangers: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for profile in await ctx.session.scalars(select(TradeRouteProfileRow).where(TradeRouteProfileRow.status.in_(list(LIVE_STATUSES)))):
        route = await ctx.session.get(EntityRow, profile.route_entity_id)
        found = ((stat(route, "danger") or 0), (stat(route, "capacity") or 0)) if route is not None else (0, 0)
        dangers[profile.first_market_id].append(found)
        dangers[profile.second_market_id].append(found)
    return dangers


def access_pct(rules: Rules, roads: int, routes: list[tuple[int, int]]) -> int:
    table = rules.market_access
    dangers = [danger for danger, _ in routes]
    carried = sum(capacity for _, capacity in routes)
    reach = table.base_pct + roads * table.per_road + len(routes) * table.per_route + carried * table.per_10_capacity / 10
    risk = sum(dangers) / len(dangers) if dangers else 0
    return clamp_int(reach * (1 - risk * table.danger_pct / PERCENT / PERCENT), 0, PERCENT)


async def gauge_access(ctx: TickContext, book: EconomyBook) -> int:
    dangers = await route_dangers(ctx)
    gauged = 0
    for community in unheld(book.communities):
        infra = await ctx.session.get(SettlementInfrastructureRow, community.id)
        row = industry_row(ctx, book, community.id)
        if "market_access" not in row.locked:
            row.market_access = access_pct(ctx.rules, infra.roads if infra is not None else 0, dangers.get(community.id, []))
            gauged += 1
        if "black_market" not in row.locked:
            row.black_market = 0
    return gauged


def sold_share(rules: Rules, row: CommunityIndustryRow | None) -> float:
    access = (row.market_access if row is not None else PERCENT) / PERCENT
    return access + (1 - access) * rules.market_access.unsold_pct / PERCENT
