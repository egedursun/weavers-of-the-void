from collections import defaultdict

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import RouteScope
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.travel import RouteClosure
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.routes import current_calendar, forgotten_world_ids, route_status
from aerona.engine.economy.purse import receive_coin
from aerona.engine.economy.stocks import goods_of
from aerona.engine.eras.effects import tech_factor
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

StockKey = tuple[object, object, object]


def trade_cost_pct(rules: Rules, scope: RouteScope) -> int:
    table = rules.cosmography
    return {
        RouteScope.SYSTEM: 0,
        RouteScope.STELLAR: table.stellar_trade_cost_pct,
        RouteScope.GALACTIC: table.galactic_trade_cost_pct,
        RouteScope.INTERGALACTIC: table.intergalactic_trade_cost_pct,
        RouteScope.INTERCLUSTER: table.intercluster_trade_cost_pct,
        RouteScope.INTERDIMENSIONAL: table.interdimensional_trade_cost_pct,
    }[scope]


def news_delay(rules: Rules, scope: RouteScope | None) -> int:
    table = rules.cosmography
    return {
        RouteScope.GALACTIC: table.galactic_news_epochs,
        RouteScope.INTERGALACTIC: table.intergalactic_news_epochs,
        RouteScope.INTERCLUSTER: table.intercluster_news_epochs,
        RouteScope.INTERDIMENSIONAL: table.interdimensional_news_epochs,
    }.get(scope or RouteScope.STELLAR, 0)


async def market_of(ctx: TickContext, world_id: int, markets: dict[int, EntityRow | None]) -> EntityRow | None:
    if world_id not in markets:
        towns = [town for town in await canon(ctx.session, [EntityType.SETTLEMENT], world_id) if not held(town.id)]
        markets[world_id] = max(towns, key=lambda town: (stat_or(town, "population", 0), -town.id), default=None)
    return markets[world_id]


async def stocks_of(ctx: TickContext, community_id: int) -> dict[StockKey, CommunityStockRow]:
    rows = await ctx.session.scalars(select(CommunityStockRow).where(CommunityStockRow.community_entity_id == community_id).order_by(CommunityStockRow.id))
    return {(row.commodity, row.material, row.world_material_id): row for row in rows}


async def carry(ctx: TickContext, route: RouteRow, scope: RouteScope, first: EntityRow, second: EntityRow) -> tuple[int, int]:
    table = ctx.rules.cosmography
    mine, theirs = await stocks_of(ctx, first.id), await stocks_of(ctx, second.id)
    gaps: list[tuple[int, StockKey, CommunityStockRow, CommunityStockRow | None, EntityRow]] = []
    for key in sorted(set(mine) | set(theirs), key=str):
        a, b = mine.get(key), theirs.get(key)
        a_qty, b_qty = (a.quantity if a is not None else 0), (b.quantity if b is not None else 0)
        if a is not None and a_qty > b_qty and not a.held:
            gaps.append(((a_qty - b_qty) * table.trade_share_pct // PERCENT // 2, key, a, b, second))
        elif b is not None and b_qty > a_qty and not b.held:
            gaps.append(((b_qty - a_qty) * table.trade_share_pct // PERCENT // 2, key, b, a, first))
    moved = delivered_total = 0
    cost = trade_cost_pct(ctx.rules, scope) / PERCENT
    stolen = route.piracy * table.piracy_loss_pct / PERCENT / PERCENT
    room = round(route.capacity * await tech_factor(ctx.session, ctx.rules, first.id, EraChannel.WORLD_ROUTES))
    for wanted, _key, source, target, buyer in sorted(gaps, key=lambda gap: (-gap[0], str(gap[1])))[: table.trade_lines]:
        amount = min(wanted, room)
        if amount <= 0 or (target is not None and target.held):
            continue
        room -= amount
        ledger = goods_of(ctx.session, ctx.epoch)
        sent = -await ledger.shift_lot(source, -amount, GoodsFlow.TRADE)
        arrived = round(sent * (1 - cost) * (1 - min(1.0, stolen)))
        arrived = await ledger.add(
            buyer.id, source.commodity, arrived, GoodsFlow.TRADE, material=source.material, world_material_id=source.world_material_id, quality=source.quality
        )
        moved += sent
        delivered_total += arrived
    return moved, delivered_total


async def lawful_ends(ctx: TickContext, ends: list[EntityRow | None]) -> int:
    claims = [await law_param(ctx.session, end.id, LawKind.SPACE_LAW, "claims") for end in ends if end is not None]
    return sum(1 for claim in claims if claim == "shared") - sum(1 for claim in claims if claim == "open")


async def tend_route(ctx: TickContext, route: RouteRow, moved: int, lawful: int = 0) -> None:
    table = ctx.rules.cosmography
    if "traffic" not in route.locked:
        route.traffic = moved
    busy = route.traffic >= table.busy_traffic
    if "wear" not in route.locked:
        route.wear = clamp_percent(route.wear + route.traffic // table.traffic_wear - (0 if busy else table.wear_repair))
    if "guarded" not in route.locked:
        route.guarded = route.toll_controller_entity_id is not None and (route.guarded or route.piracy >= table.guard_piracy)
    if "piracy" not in route.locked:
        guard = table.guard_piracy_cut if route.guarded else 0
        route.piracy = clamp_percent(route.piracy + (table.piracy_growth if busy else -table.piracy_decay) - lawful * table.space_law_piracy - guard)
    if "danger" not in route.locked and route.wear:
        route.danger = clamp_percent(max(route.danger, route.wear * table.wear_danger_pct // PERCENT))
    if route.wear >= PERCENT and "active" not in route.locked:
        route.active, route.closure = False, RouteClosure.WORN


async def cosmic_trade(ctx: TickContext) -> int:
    cosmography = await Cosmography.load(ctx.session)
    calendar = await current_calendar(ctx.session, ctx.rules, ctx.epoch)
    forgotten = await forgotten_world_ids(ctx.session)
    markets: dict[int, EntityRow | None] = {}
    tolls: dict[int, int] = defaultdict(int)
    carried = 0
    for route in list(await ctx.session.scalars(select(RouteRow).where(RouteRow.active.is_(True)).order_by(RouteRow.id))):
        if held(route.world_a_id, route.world_b_id) or not route_status(route, calendar, forgotten).is_open:
            continue
        first, second = await market_of(ctx, route.world_a_id, markets), await market_of(ctx, route.world_b_id, markets)
        moved = delivered = 0
        if first is not None and second is not None:
            moved, delivered = await carry(ctx, route, cosmography.scope_by_id(route.world_a_id, route.world_b_id), first, second)
        await tend_route(ctx, route, moved + (route.traffic if moved == 0 and "traffic" in route.locked else 0), await lawful_ends(ctx, [first, second]))
        if route.toll_controller_entity_id is not None and route.toll_pct and delivered:
            tolls[route.toll_controller_entity_id] += delivered * (route.toll_pct + (ctx.rules.cosmography.guard_toll_pct if route.guarded else 0)) // PERCENT
        carried += moved
    for controller_id, amount in sorted(tolls.items()):
        controller = await ctx.session.get(EntityRow, controller_id)
        if controller is not None and not held(controller.id):
            await receive_coin(ctx.session, ctx.rules, controller, amount)
    await ctx.session.flush()
    return carried
