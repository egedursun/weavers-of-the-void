from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agrarian import BrandRow
from aerona.db.tables.commerce import LeaseRow, PromotionRow, ShopGoodRow, ShopRow, SupplyTierRow
from aerona.db.tables.economy import LoanRow, MarketPriceRow, TradeRouteProfileRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.commerce import LeaseDefault, ShopForm, SupplyTier
from aerona.domain.enums.economy import CommodityKind, TradeMode, TradeRouteStatus, WorkshopKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import TradeRouteStats
from aerona.engine.commerce.seed import seed_commerce
from aerona.engine.commerce.trade import CommerceTally, keep_commerce, keep_lease, retail_short, without_shops
from aerona.engine.context import TickContext
from aerona.engine.economy.household import Wear
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def town(session: AsyncSession, world: CoreWorld) -> EntityRow:
    found = await settlement(session, "Ardun", world, world.regions[0])
    session.add(SettlementProfileRow(settlement_entity_id=found.id, size_tier=SizeTier.TOWN, unrest=10, locked=[], foreigners={}))
    await session.flush()
    return found


async def trader(session: AsyncSession, world: CoreWorld, name: str, place: int, **profile: int) -> EntityRow:
    being = await mortal(session, name, world, place)
    session.add(MortalProfileRow(entity_id=being.id, locked=[], **({"wealth": 50, "honour": 50} | profile)))
    await session.flush()
    return being


def tuned(ctx: TickContext, **values: int) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(commerce=values)))


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("commerce.")).order_by(IncidentRow.id)))


async def test_a_town_without_shops_goes_without_part_of_its_worn_goods(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world)
    assert await retail_short(session, 15, home.id) == 15
    assert without_shops(Wear(wanted={CommodityKind.CLOTH: 10}, got={CommodityKind.CLOTH: 10}), 15).got[CommodityKind.CLOTH] == 9
    keeper = await trader(session, world, "Ama", home.id)
    session.add(ShopRow(settlement_entity_id=home.id, keeper_node_id=keeper.id, form=ShopForm.STALL, locked=[]))
    await session.flush()
    assert await retail_short(session, 15, home.id) == 0


async def test_a_shop_earns_for_its_keeper_and_closes_when_the_keeper_is_gone(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world)
    keeper = await trader(session, world, "Kel", home.id, wealth=10)
    shop = ShopRow(settlement_entity_id=home.id, keeper_node_id=keeper.id, form=ShopForm.SHOP, margin=50, stock=10, locked=[])
    session.add(shop)
    await session.flush()
    tally = await keep_commerce(ctx)
    profile = await session.get(MortalProfileRow, keeper.id)
    assert tally.sold > 0 and profile is not None and profile.wealth > 10
    keeper.status, keeper.end_epoch = EntityStatus.DEAD, ctx.epoch
    await session.flush()
    assert (await keep_commerce(ctx)).closed == 1
    assert "commerce.shop_closed" in await kinds_of(session)


async def test_a_holder_of_most_of_a_tier_corners_it(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world)
    holder = await trader(session, world, "Dun", home.id, wealth=0)
    session.add(MarketPriceRow(market_entity_id=home.id, commodity=CommodityKind.GRAIN, epoch=ctx.epoch, price=100, supply=50, demand=50))
    tier = SupplyTierRow(
        market_entity_id=home.id, commodity=CommodityKind.GRAIN, tier=SupplyTier.WHOLESALE, holder_node_id=holder.id, share=90, margin=20, locked=[]
    )
    session.add(tier)
    await session.flush()
    tally = await keep_commerce(ctx)
    profile = await session.get(SettlementProfileRow, home.id)
    assert tier.cornered and tier.margin == 30 and tally.tier_income > 0
    assert profile is not None and profile.unrest > 10
    assert "commerce.tier_cornered" in await kinds_of(session)


async def test_a_towns_own_common_trade_is_never_a_corner_and_old_corners_are_freed(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world)
    session.add(MarketPriceRow(market_entity_id=home.id, commodity=CommodityKind.GRAIN, epoch=ctx.epoch, price=100, supply=50, demand=50))
    fresh = SupplyTierRow(market_entity_id=home.id, tier=SupplyTier.RETAIL, holder_node_id=home.id, share=100, margin=20, locked=[])
    stale = SupplyTierRow(market_entity_id=home.id, tier=SupplyTier.WHOLESALE, holder_node_id=home.id, share=100, margin=99, cornered=True, locked=[])
    session.add_all([fresh, stale])
    await session.flush()
    seeded = await seed_commerce(ctx)
    await keep_commerce(ctx)
    profile = await session.get(SettlementProfileRow, home.id)
    assert seeded.freed == 1 and not stale.cornered and stale.margin == ctx.rules.commerce.wholesale_margin_pct
    assert not fresh.cornered and fresh.margin == 20
    assert profile is not None and profile.unrest == 10
    assert "commerce.tier_cornered" not in await kinds_of(session)


async def test_a_false_claim_is_found_out_and_costs_honour(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world)
    holder = await trader(session, world, "Iro", home.id)
    session.add(PromotionRow(holder_node_id=holder.id, reach=100, accuracy=0, cost=1, locked=[]))
    await session.flush()
    tally = await keep_commerce(ctx)
    profile = await session.get(MortalProfileRow, holder.id)
    assert tally.exposed == 1 and profile is not None and profile.honour < 50
    assert "commerce.claim_exposed" in await kinds_of(session)


async def test_a_lease_pays_rent_and_an_unpaid_rent_becomes_a_debt(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world)
    owner, lessee = await trader(session, world, "Vael", home.id, wealth=10), await trader(session, world, "Orin", home.id, wealth=40)
    lease = LeaseRow(owner_node_id=owner.id, lessee_node_id=lessee.id, thing_node_id=home.id, rent=5, term_epochs=5, signed_epoch=ctx.epoch, locked=[])
    session.add(lease)
    await session.flush()
    tally = CommerceTally()
    await keep_lease(tuned(ctx, lease_default_chance_pct=0, upkeep_cost=0), lease, tally)
    paid = await session.get(MortalProfileRow, owner.id)
    assert tally.rent_paid == 5 and paid is not None and paid.wealth == 15
    lease.on_default = LeaseDefault.DEBT
    await keep_lease(tuned(ctx, lease_default_chance_pct=100), lease, tally)
    debt = await session.scalar(select(LoanRow).where(LoanRow.borrower_entity_id == lessee.id))
    assert tally.defaulted == 1 and debt is not None and debt.principal == 5
    assert "commerce.lease_defaulted" in await kinds_of(session)


async def test_markets_get_a_retail_tier_and_branded_workshops_become_shops(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world)
    smith = await trader(session, world, "Lir", home.id)
    session.add(WorkshopRow(community_entity_id=home.id, kind=WorkshopKind.MARKET, level=1, built_epoch=0))
    forge = WorkshopRow(community_entity_id=home.id, kind=WorkshopKind.FORGE, level=1, built_epoch=0, owner_node_id=smith.id)
    session.add(forge)
    await session.flush()
    session.add(BrandRow(workshop_id=forge.id, community_entity_id=home.id, owner_node_id=smith.id, name="Lir's Iron", locked=[]))
    await session.flush()
    tally = await seed_commerce(ctx)
    shop = await session.scalar(select(ShopRow).where(ShopRow.keeper_node_id == smith.id))
    assert tally.tiers == 1 and tally.shops == 1 and shop is not None
    assert await session.get(ShopGoodRow, (shop.id, CommodityKind.TOOLS)) is not None


async def test_a_market_on_a_trade_route_also_keeps_a_wholesale_tier(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world)
    other = await settlement(session, "Lowmere", world, world.regions[1])
    road = await entity(session, "Long Road", EntityType.TRADE_ROUTE, TradeRouteStats(capacity=40), world_id=world.world.id)
    session.add(WorkshopRow(community_entity_id=home.id, kind=WorkshopKind.MARKET, level=1, built_epoch=0))
    session.add(
        TradeRouteProfileRow(
            route_entity_id=road.id,
            first_market_id=home.id,
            second_market_id=other.id,
            mode=TradeMode.ROAD,
            status=TradeRouteStatus.OPEN,
            length=2,
            founded_epoch=0,
            locked=[],
        )
    )
    await session.flush()
    await seed_commerce(ctx)
    tiers = {row.tier: row.margin for row in await session.scalars(select(SupplyTierRow).where(SupplyTierRow.market_entity_id == home.id))}
    assert tiers == {SupplyTier.RETAIL: ctx.rules.commerce.retail_margin_pct, SupplyTier.WHOLESALE: ctx.rules.commerce.wholesale_margin_pct}
