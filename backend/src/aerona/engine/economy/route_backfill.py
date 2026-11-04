from collections import defaultdict

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.economy import TradeFlowRow, TradeRouteTollRow
from aerona.db.tables.military import WarAimRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.military import WarAimKind
from aerona.domain.enums.war import WarCause, WarSide, WarStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.chokepoints import contested_route
from aerona.engine.economy.toll_polities import Realms, fund_polity
from aerona.engine.primitives.numbers import round_half_up

ROUTE_FIXUP = "economy.route_depth_backfill"
PAST_TOLLS = "tolls of the ages before the ledger"


async def ledger_past_tolls(ctx: TickContext, realms: Realms) -> int:
    paid: dict[int, int] = {
        route: int(total)
        for route, total in await ctx.session.execute(
            select(TradeFlowRow.route_entity_id, func.coalesce(func.sum(TradeFlowRow.toll_paid), 0)).group_by(TradeFlowRow.route_entity_id)
        )
    }
    tolls: dict[int, list[TradeRouteTollRow]] = defaultdict(list)
    for toll in await ctx.session.scalars(select(TradeRouteTollRow).order_by(TradeRouteTollRow.route_entity_id, TradeRouteTollRow.region_entity_id)):
        toll.polity_entity_id = realms.treasury_of(toll.controller_entity_id)
        tolls[toll.route_entity_id].append(toll)
    funded = 0
    for route, rows in sorted(tolls.items()):
        rates = sum(row.rate_pct for row in rows)
        if not rates or not paid.get(route):
            continue
        for row in rows:
            if row.polity_entity_id is None:
                continue
            part = round_half_up(paid[route] * row.rate_pct / rates)
            share = part if row.polity_entity_id == row.controller_entity_id else round_half_up(part * ctx.rules.tolls.polity_share_pct / PERCENT)
            funded += await fund_polity(ctx, row.polity_entity_id, share, PAST_TOLLS)
    return funded


async def aim_route_wars(ctx: TickContext) -> int:
    wars = list(await ctx.session.scalars(select(WarRow).where(WarRow.cause == WarCause.TRADE_ROUTE, WarRow.status != WarStatus.ENDED).order_by(WarRow.id)))
    made = 0
    for war in wars:
        sides = list(await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id, WarSideRow.left_epoch.is_(None))))
        attackers = [side.entity_id for side in sides if side.side is WarSide.ATTACKER]
        defenders = [side.entity_id for side in sides if side.side is WarSide.DEFENDER]
        if not attackers or not defenders:
            continue
        aimed = await ctx.session.scalar(select(WarAimRow.id).where(WarAimRow.war_id == war.id, WarAimRow.kind == WarAimKind.SEIZE_ROUTE).limit(1))
        if aimed is not None:
            continue
        attacker, defender = min(attackers), min(defenders)
        target = await contested_route(ctx.session, attacker, defender)
        ctx.session.add(WarAimRow(war_id=war.id, side_entity_id=attacker, kind=WarAimKind.SEIZE_ROUTE, target_entity_id=target, params={}, achieved=0))
        made += 1
    return made


async def route_backfill(ctx: TickContext, realms: Realms) -> dict[str, int]:
    if await ctx.session.get(AppliedFixupRow, ROUTE_FIXUP) is not None:
        return {}
    result = {"polity_tolls": await ledger_past_tolls(ctx, realms), "route_aims": await aim_route_wars(ctx)}
    ctx.session.add(AppliedFixupRow(key=ROUTE_FIXUP, result=result))
    await ctx.session.flush()
    return result
