from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commerce_shapes import LEASE_UPKEEP_PCT, PROMOTION_PULL_PCT, SHOP_TURNOVER_PCT, TIER_INCOME_PCT
from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import BrandRow
from aerona.db.tables.commerce import LeaseRow, PromotionRow, ShopRow, SupplyTierRow
from aerona.db.tables.economy import LoanRow, MarketPriceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.commerce import LeaseDefault, LeaseUpkeep, SupplyTier
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.engine.commerce.dealings import DealingsTally, lease_shops, promote_brands
from aerona.engine.context import TickContext
from aerona.engine.economy.household import Wear
from aerona.engine.economy.purse import give_coin, points_of, shift_points
from aerona.engine.polity.laws import ruling_law
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

TEN = 10
HONEST = 50
RENT_PURPOSE = "unpaid rent"


@dataclass
class CommerceTally:
    sold: int = 0
    closed: int = 0
    tier_income: int = 0
    cornered: int = 0
    promoted: int = 0
    exposed: int = 0
    rent_paid: int = 0
    defaulted: int = 0
    leases_ended: int = 0
    leased: int = 0


async def living(session: AsyncSession, node_id: int | None) -> EntityRow | None:
    being = await session.get(EntityRow, node_id) if node_id is not None else None
    return being if being is not None and being.status is EntityStatus.CANON else None


async def retail_short(session: AsyncSession, rules_pct: int, town_id: int) -> int:
    shop = await session.scalar(select(ShopRow.id).where(ShopRow.settlement_entity_id == town_id).limit(1))
    if shop is not None:
        return 0
    tier = await session.scalar(select(SupplyTierRow.id).where(SupplyTierRow.market_entity_id == town_id, SupplyTierRow.tier == SupplyTier.RETAIL).limit(1))
    if tier is not None:
        return 0
    peddled = await session.scalar(select(SupplyTierRow.id).where(SupplyTierRow.market_entity_id == town_id, SupplyTierRow.tier == SupplyTier.PEDDLER).limit(1))
    return rules_pct // 2 if peddled is not None else rules_pct


def without_shops(worn: Wear, short: int) -> Wear:
    if short <= 0:
        return worn
    return Wear(wanted=dict(worn.wanted), got={kind: round_half_up(amount * (PERCENT - short) / PERCENT) for kind, amount in worn.got.items()})


async def close_shop(ctx: TickContext, shop: ShopRow, why: str, tally: CommerceTally) -> None:
    await record(ctx, "commerce.shop_closed", roles={IncidentRole.PLACE: shop.settlement_entity_id}, facts={"form": shop.form, "why": why})
    await ctx.session.delete(shop)
    tally.closed += 1


async def keep_shop(ctx: TickContext, shop: ShopRow, tally: CommerceTally) -> None:
    table = ctx.rules.commerce
    keeper = await living(ctx.session, shop.keeper_node_id)
    if keeper is None:
        await close_shop(ctx, shop, "its keeper is gone", tally)
        return
    if shop.stock <= 0:
        await close_shop(ctx, shop, "its shelves stood empty", tally)
        return
    sold = min(shop.stock, table.per_epoch(table.shop_turnover * SHOP_TURNOVER_PCT[shop.form] / PERCENT))
    if "stock" not in (shop.locked or []):
        shop.stock -= sold
    income = round_half_up(sold * shop.margin / TEN)
    await shift_points(ctx.session, keeper, income)
    if await points_of(ctx.session, keeper) >= sold and "stock" not in (shop.locked or []):
        await shift_points(ctx.session, keeper, -sold)
        shop.stock += sold
    tally.sold += sold
    town = await ctx.session.get(EntityRow, shop.settlement_entity_id)
    if town is not None and shop.credit > 0 and not held(town.id):
        gain = shop.credit / TEN * table.shop_credit_prosperity / TEN
        with explaining():
            term("commerce.shop_credit_prosperity", gain, source_node_id=keeper.id)
            shift_stat(town, "prosperity", gain, low=0, high=PERCENT)


async def traded_value(session: AsyncSession, tier: SupplyTierRow) -> int:
    latest = select(func.max(MarketPriceRow.epoch)).where(MarketPriceRow.market_entity_id == tier.market_entity_id).scalar_subquery()
    statement = select(MarketPriceRow).where(MarketPriceRow.market_entity_id == tier.market_entity_id, MarketPriceRow.epoch == latest)
    if tier.commodity is not None:
        statement = statement.where(MarketPriceRow.commodity == tier.commodity)
    return sum(row.price * min(row.supply, row.demand) for row in await session.scalars(statement.order_by(MarketPriceRow.commodity)))


async def keep_tier(ctx: TickContext, tier: SupplyTierRow, tally: CommerceTally) -> None:
    table = ctx.rules.commerce
    holder = await living(ctx.session, tier.holder_node_id)
    if holder is None:
        await ctx.session.delete(tier)
        return
    income = round_half_up(
        await traded_value(ctx.session, tier)
        * table.tier_income_pct
        / PERCENT
        * tier.share
        / PERCENT
        * tier.margin
        / PERCENT
        * TIER_INCOME_PCT[tier.tier]
        / PERCENT
    )
    if income:
        await give_coin(ctx.session, ctx.rules, holder, income)
        tally.tier_income += income
    common = tier.holder_node_id == tier.market_entity_id
    if not common and not tier.cornered and tier.share >= table.corner_share and "cornered" not in (tier.locked or []):
        tier.cornered = True
        if "margin" not in (tier.locked or []):
            tier.margin = clamp_int(tier.margin + table.corner_margin, 0, 2 * PERCENT)
        await record(
            ctx,
            "commerce.tier_cornered",
            roles={IncidentRole.ACTOR: holder.id, IncidentRole.PLACE: tier.market_entity_id},
            facts={"tier": tier.tier, "share": tier.share},
        )
        tally.cornered += 1
    if tier.cornered and not common:
        profile = await ctx.session.get(SettlementProfileRow, tier.market_entity_id)
        if profile is not None and not held(tier.market_entity_id) and "unrest" not in (profile.locked or []):
            with explaining():
                term("commerce.corner_unrest", table.corner_unrest, source_node_id=holder.id)
                profile.unrest = clamp_int(profile.unrest + table.corner_unrest, 0, PERCENT)


async def lose_honour(ctx: TickContext, holder: EntityRow, amount: int) -> None:
    profile = await ctx.session.get(MortalProfileRow, holder.id)
    if profile is not None and "honour" not in (profile.locked or []):
        with explaining():
            term("commerce.false_claim_trust_loss", -amount, source_node_id=holder.id)
            profile.honour = clamp_int(profile.honour - amount, 0, PERCENT)


async def keep_promotion(ctx: TickContext, promotion: PromotionRow, tally: CommerceTally) -> None:
    table = ctx.rules.commerce
    holder = await living(ctx.session, promotion.holder_node_id)
    if holder is None or await points_of(ctx.session, holder) < promotion.cost:
        await ctx.session.delete(promotion)
        return
    await shift_points(ctx.session, holder, -promotion.cost)
    brand = await ctx.session.get(BrandRow, promotion.brand_id) if promotion.brand_id is not None else None
    if brand is not None and "reputation" not in (brand.locked or []):
        pull = table.promotion_demand_pct * promotion.reach / (PERCENT * TEN) * PROMOTION_PULL_PCT[promotion.medium] / PERCENT
        with explaining():
            term("commerce.promotion_demand_pct", pull, source_node_id=holder.id)
            brand.reputation = clamp_int(brand.reputation + round_half_up(pull), 0, PERCENT)
    tally.promoted += 1
    if promotion.exposed or promotion.accuracy >= HONEST:
        return
    odds = (PERCENT - promotion.accuracy) * promotion.reach / PERCENT
    if not ctx.rng(f"claim_exposed.{promotion.id}.{ctx.epoch}").chance(odds):
        return
    promotion.exposed = True
    if brand is not None and "reputation" not in (brand.locked or []):
        brand.reputation = clamp_int(brand.reputation - table.false_claim_trust_loss, 0, PERCENT)
    await lose_honour(ctx, holder, table.false_claim_trust_loss)
    fair = holder.location_id is not None and await ruling_law(ctx.session, holder.location_id, LawKind.FAIR_MARKET) is not None
    if fair:
        await shift_points(ctx.session, holder, -table.false_claim_trust_loss)
    await record(
        ctx,
        "commerce.claim_exposed",
        roles={IncidentRole.ACTOR: holder.id},
        facts={"medium": promotion.medium, "accuracy": promotion.accuracy, "fined": int(fair)},
        place=holder.location_id,
    )
    tally.exposed += 1


async def default(ctx: TickContext, lease: LeaseRow, owner: EntityRow, lessee: EntityRow, tally: CommerceTally) -> None:
    await record(
        ctx,
        "commerce.lease_defaulted",
        roles={IncidentRole.ACTOR: lessee.id, IncidentRole.TARGET: owner.id},
        facts={"thing": lease.thing, "on_default": lease.on_default, "rent": lease.rent},
        place=lessee.location_id,
    )
    tally.defaulted += 1
    if lease.on_default is LeaseDefault.EVICTION:
        await ctx.session.delete(lease)
        return
    if lease.on_default is LeaseDefault.COURT:
        await lose_honour(ctx, lessee, ctx.rules.commerce.false_claim_trust_loss)
    ctx.session.add(
        LoanRow(
            lender_entity_id=owner.id,
            borrower_entity_id=lessee.id,
            currency_id=None,
            principal=lease.rent,
            interest_pct=0,
            issued_epoch=ctx.epoch,
            due_epoch=ctx.epoch + lease.term_epochs,
            status=LoanStatus.OPEN,
            purpose=RENT_PURPOSE if lease.on_default is LeaseDefault.DEBT else f"{RENT_PURPOSE}, brought to court",
        )
    )


async def keep_lease(ctx: TickContext, lease: LeaseRow, tally: CommerceTally) -> None:
    table = ctx.rules.commerce
    owner, lessee = await living(ctx.session, lease.owner_node_id), await living(ctx.session, lease.lessee_node_id)
    if owner is None or lessee is None or (ctx.epoch >= lease.signed_epoch + lease.term_epochs and "term_epochs" not in (lease.locked or [])):
        await ctx.session.delete(lease)
        tally.leases_ended += 1
        return
    unpaid = await points_of(ctx.session, lessee) < lease.rent or ctx.rng(f"lease_default.{lease.id}.{ctx.epoch}").chance(table.lease_default_chance_pct)
    if unpaid:
        await default(ctx, lease, owner, lessee, tally)
        return
    await shift_points(ctx.session, lessee, -lease.rent)
    await shift_points(ctx.session, owner, lease.rent)
    tally.rent_paid += lease.rent
    payers = {LeaseUpkeep.OWNER: (owner,), LeaseUpkeep.LESSEE: (lessee,), LeaseUpkeep.SHARED: (owner, lessee)}[lease.upkeep]
    upkeep = round_half_up(table.upkeep_cost * LEASE_UPKEEP_PCT[lease.thing] / PERCENT)
    for payer in payers:
        await shift_points(ctx.session, payer, -upkeep)


async def keep_commerce(ctx: TickContext) -> CommerceTally:
    tally = CommerceTally()
    for shop in list(await ctx.session.scalars(select(ShopRow).order_by(ShopRow.id))):
        if not held(shop.keeper_node_id) and not held(shop.settlement_entity_id):
            await keep_shop(ctx, shop, tally)
    for tier in list(await ctx.session.scalars(select(SupplyTierRow).order_by(SupplyTierRow.id))):
        if not held(tier.holder_node_id) and not held(tier.market_entity_id):
            await keep_tier(ctx, tier, tally)
    for promotion in list(await ctx.session.scalars(select(PromotionRow).order_by(PromotionRow.id))):
        if not held(promotion.holder_node_id):
            await keep_promotion(ctx, promotion, tally)
    for lease in list(await ctx.session.scalars(select(LeaseRow).order_by(LeaseRow.id))):
        if not held(lease.owner_node_id) and not held(lease.lessee_node_id):
            await keep_lease(ctx, lease, tally)
    dealings = DealingsTally()
    await promote_brands(ctx, dealings)
    await lease_shops(ctx, dealings)
    tally.promoted += dealings.promotions
    tally.leased += dealings.leases
    await ctx.session.flush()
    return tally
