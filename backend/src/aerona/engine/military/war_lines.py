from sqlalchemy import select

from aerona.catalog.goods_traits import commodities_with
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import WarProductionRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.goods_traits import CommodityTrait
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import holding
from aerona.engine.primitives.numbers import clamp_int

WAR_GOODS = commodities_with(CommodityTrait.WAR_GOOD)
CIVILIAN_GOODS = frozenset(commodities_with(CommodityTrait.CIVILIAN))
SWITCH_MARGIN = 2


async def warring_communities(ctx: TickContext) -> set[int]:
    ongoing = select(WarRow.id).where(WarRow.status != WarStatus.ENDED)
    sides = await ctx.session.scalars(select(WarSideRow.entity_id).where(WarSideRow.left_epoch.is_(None), WarSideRow.war_id.in_(ongoing)))
    found: set[int] = set()
    for entity_id in sides:
        entity = await ctx.session.get(EntityRow, entity_id)
        if entity is not None and entity.status is EntityStatus.CANON and entity.entity_type in COMMUNITY_TYPES:
            found.add(entity_id)
    return found


async def wanted_good(ctx: TickContext, community_id: int, current: CommodityKind | None) -> CommodityKind:
    stocks = {good: await holding(ctx.session, community_id, good) for good in WAR_GOODS}
    _rank, least = min(enumerate(WAR_GOODS), key=lambda pair: (stocks[pair[1]], pair[0]))
    if current in stocks and stocks[current] <= stocks[least] * SWITCH_MARGIN + PERCENT // 10:
        return current
    return least


def grow(ctx: TickContext, row: WarProductionRow) -> None:
    if "efficiency" not in row.locked:
        row.efficiency = clamp_int(row.efficiency + ctx.rules.war_conduct.efficiency_gain, 0, ctx.rules.war_conduct.efficiency_cap)


async def keep_war_lines(ctx: TickContext) -> dict[str, int]:
    counts = {"opened": 0, "sustained": 0, "switched": 0, "stood_down": 0}
    warring = await warring_communities(ctx)
    for community_id in sorted(warring):
        if held(community_id):
            continue
        row = await ctx.session.get(WarProductionRow, community_id)
        want = await wanted_good(ctx, community_id, row.commodity if row is not None else None)
        if row is None:
            ctx.session.add(WarProductionRow(community_entity_id=community_id, commodity=want, efficiency=0, converted=True, since_epoch=ctx.epoch, locked=[]))
            counts["opened"] += 1
            continue
        if "converted" not in row.locked:
            row.converted = True
        if row.commodity is want or "commodity" in row.locked:
            grow(ctx, row)
            counts["sustained"] += 1
            continue
        row.commodity, row.since_epoch = want, ctx.epoch
        if "efficiency" not in row.locked:
            row.efficiency = 0
        counts["switched"] += 1
    for row in list(await ctx.session.scalars(select(WarProductionRow).where(WarProductionRow.converted.is_(True)))):
        if row.community_entity_id in warring or held(row.community_entity_id) or "converted" in row.locked:
            continue
        row.converted = False
        if "efficiency" not in row.locked:
            row.efficiency = max(0, row.efficiency - ctx.rules.war_conduct.efficiency_gain)
        counts["stood_down"] += 1
    return counts


async def war_output(ctx: TickContext, community_id: int, output: CommodityKind) -> float:
    row = await ctx.session.get(WarProductionRow, community_id)
    if row is None or not row.converted:
        return 1.0
    if output is row.commodity:
        return 1 + row.efficiency / PERCENT
    if output in CIVILIAN_GOODS:
        return 1 - ctx.rules.war_conduct.civilian_cut_pct / PERCENT
    return 1.0
