from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.goods_tables import WORKSHOP_GOODS
from aerona.db.tables.agrarian import BrandRow
from aerona.db.tables.commerce import ShopGoodRow, ShopRow, SupplyTierRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.economy import TradeRouteProfileRow, WorkshopRow
from aerona.db.write_guard import held
from aerona.domain.enums.commerce import ShopForm, SupplyTier
from aerona.domain.enums.economy import WorkshopKind
from aerona.engine.commerce.trade import living
from aerona.engine.context import TickContext

COMMON_TIERS_FIXUP = "commerce.common_tiers"


@dataclass
class CommerceSeedTally:
    tiers: int = 0
    shops: int = 0
    freed: int = 0


async def free_common_tiers(ctx: TickContext, tally: CommerceSeedTally) -> None:
    if await ctx.session.get(AppliedFixupRow, COMMON_TIERS_FIXUP) is not None:
        return
    table = ctx.rules.commerce
    margins = {SupplyTier.RETAIL: table.retail_margin_pct, SupplyTier.WHOLESALE: table.wholesale_margin_pct}
    rows = await ctx.session.scalars(
        select(SupplyTierRow).where(SupplyTierRow.cornered.is_(True), SupplyTierRow.holder_node_id == SupplyTierRow.market_entity_id).order_by(SupplyTierRow.id)
    )
    for tier in list(rows):
        if held(tier.market_entity_id) or "cornered" in (tier.locked or []):
            continue
        tier.cornered = False
        if "margin" not in (tier.locked or []):
            tier.margin = margins.get(tier.tier, tier.margin)
        tally.freed += 1
    ctx.session.add(AppliedFixupRow(key=COMMON_TIERS_FIXUP, result={"freed": tally.freed}))


async def seed_tiers(ctx: TickContext, tally: CommerceSeedTally) -> None:
    tiered = set(await ctx.session.scalars(select(SupplyTierRow.market_entity_id)))
    markets = await ctx.session.scalars(
        select(WorkshopRow.community_entity_id).where(WorkshopRow.kind == WorkshopKind.MARKET).order_by(WorkshopRow.community_entity_id).distinct()
    )
    traders = set(await ctx.session.scalars(select(TradeRouteProfileRow.first_market_id))) | set(
        await ctx.session.scalars(select(TradeRouteProfileRow.second_market_id))
    )
    table = ctx.rules.commerce
    for market_id in list(markets):
        if market_id in tiered or held(market_id) or await living(ctx.session, market_id) is None:
            continue
        ctx.session.add(
            SupplyTierRow(market_entity_id=market_id, tier=SupplyTier.RETAIL, holder_node_id=market_id, share=100, margin=table.retail_margin_pct, locked=[])
        )
        if market_id in traders:
            ctx.session.add(
                SupplyTierRow(
                    market_entity_id=market_id, tier=SupplyTier.WHOLESALE, holder_node_id=market_id, share=100, margin=table.wholesale_margin_pct, locked=[]
                )
            )
        tiered.add(market_id)
        tally.tiers += 1


async def seed_shops(ctx: TickContext, tally: CommerceSeedTally) -> None:
    kept = {(shop.settlement_entity_id, shop.keeper_node_id) for shop in await ctx.session.scalars(select(ShopRow))}
    rows = await ctx.session.execute(
        select(BrandRow, WorkshopRow).join(WorkshopRow, WorkshopRow.id == BrandRow.workshop_id).where(BrandRow.owner_node_id.is_not(None)).order_by(BrandRow.id)
    )
    for brand, workshop in list(rows):
        keeper = brand.owner_node_id
        if keeper is None or (brand.community_entity_id, keeper) in kept or held(keeper) or held(brand.community_entity_id):
            continue
        if await living(ctx.session, keeper) is None:
            continue
        shop = ShopRow(
            settlement_entity_id=brand.community_entity_id,
            structure_entity_id=workshop.structure_entity_id,
            keeper_node_id=keeper,
            form=ShopForm.HOUSE_TRADE,
            margin=ctx.rules.commerce.retail_margin_pct,
            opened_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(shop)
        await ctx.session.flush()
        good = WORKSHOP_GOODS.get(workshop.kind)
        if good is not None:
            ctx.session.add(ShopGoodRow(shop_id=shop.id, commodity=good, keeper_node_id=keeper, locked=[]))
        kept.add((brand.community_entity_id, keeper))
        tally.shops += 1


async def seed_commerce(ctx: TickContext) -> CommerceSeedTally:
    tally = CommerceSeedTally()
    await free_common_tiers(ctx, tally)
    await seed_tiers(ctx, tally)
    await seed_shops(ctx, tally)
    await ctx.session.flush()
    return tally
