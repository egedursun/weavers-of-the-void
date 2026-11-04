from collections.abc import Mapping

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.needs import CLASS_INCOME, SERVE_ORDER
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import ClassStandingRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.demography.basket import standing_of
from aerona.engine.economy.stocks import holdings
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

WEALTH_LOCK = "wealth"


def stock_value(held: Mapping[CommodityKind, int], prices: Mapping[CommodityKind, int]) -> int:
    return round_half_up(sum(quantity * prices.get(kind, PERCENT) * COMMODITIES[kind].base_price / PERCENT / PERCENT for kind, quantity in held.items()))


def wealth_targets(total: int, shares: Mapping[SocialClass, float]) -> dict[SocialClass, int]:
    weights = {social_class: max(0.0, shares.get(social_class, 0.0)) * CLASS_INCOME[social_class] for social_class in SocialClass}
    whole = sum(weights.values())
    if whole <= 0:
        return dict.fromkeys(SocialClass, 0)
    return {social_class: round_half_up(total * weight / whole) for social_class, weight in weights.items()}


def gini(wealth: Mapping[SocialClass, int], shares: Mapping[SocialClass, float]) -> int:
    present = [social_class for social_class in SocialClass if shares.get(social_class, 0.0) > 0]
    people = sum(shares[social_class] for social_class in present)
    riches = sum(max(0, wealth.get(social_class, 0)) for social_class in present)
    if len(present) < 2 or people <= 0 or riches <= 0:
        return 0
    ordered = sorted(present, key=lambda item: (max(0, wealth.get(item, 0)) / shares[item], SERVE_ORDER.index(item)))
    area = 0.0
    before = 0.0
    for social_class in ordered:
        after = before + max(0, wealth.get(social_class, 0)) / riches
        area += shares[social_class] / people * (before + after)
        before = after
    return clamp_int(round_half_up((1 - area) * PERCENT), 0, PERCENT)


def drift(rules: Rules, current: int, target: int) -> int:
    return max(0, round_half_up(current + (target - current) * rules.mobility.wealth_drift_pct / PERCENT))


async def settle_wealth(
    ctx: TickContext, community: EntityRow, society: CommunitySocietyRow, shares: Mapping[SocialClass, float], prices: Mapping[CommodityKind, int]
) -> int:
    held = await holdings(ctx.session, community.id)
    total = stock_value(held, prices) + round_half_up(
        (society.stock_food + society.stock_ore + society.stock_goods) * ctx.rules.mobility.wealth_per_supply_pct / PERCENT
    )
    targets = wealth_targets(total, shares)
    standing = await standing_of(ctx.session, community.id)
    for social_class in SocialClass:
        row = standing.get(social_class)
        if row is None:
            if shares.get(social_class, 0.0) <= 0:
                continue
            row = ClassStandingRow(community_entity_id=community.id, social_class=social_class, wealth=0, income=0, locked=[], epoch=ctx.epoch)
            ctx.session.add(row)
            standing[social_class] = row
        if WEALTH_LOCK in row.locked:
            row.income = 0
            continue
        fresh = drift(ctx.rules, row.wealth, targets.get(social_class, 0))
        row.income = fresh - row.wealth
        row.wealth = fresh
        row.epoch = ctx.epoch
    society.gini = gini({social_class: row.wealth for social_class, row in standing.items()}, shares)
    await ctx.session.flush()
    return society.gini


def per_head(row: ClassStandingRow, share: float) -> int:
    return round_half_up(row.wealth / share) if share > 0 else 0
