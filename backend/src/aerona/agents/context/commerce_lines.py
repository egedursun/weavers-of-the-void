from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import an, several, spoken
from aerona.db.tables.commerce import LeaseRow, PromotionRow, ShopGoodRow, ShopRow, SupplyTierRow
from aerona.db.tables.entities import EntityRow


async def goods_of(scope: Scope, shop_id: int) -> str:
    goods = await scope.session.scalars(select(ShopGoodRow.commodity).where(ShopGoodRow.shop_id == shop_id).order_by(ShopGoodRow.commodity))
    return ", ".join(spoken(good) for good in goods) or "nothing yet"


async def mortal_commerce_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for shop in await session.scalars(select(ShopRow).where(ShopRow.keeper_node_id == me.id).order_by(ShopRow.id)):
        found.append(
            f"you keep {an(spoken(shop.form))} in {await named(scope, shop.settlement_entity_id)} selling {await goods_of(scope, shop.id)}; "
            f"margin {shop.margin}, stock {shop.stock}, credit to customers {shop.credit}"
        )
    if me.location_id is not None:
        shops = list(
            await session.scalars(select(ShopRow).where(ShopRow.settlement_entity_id == me.location_id, ShopRow.keeper_node_id != me.id).order_by(ShopRow.id))
        )
        if shops:
            found.append("shops of your town: " + "; ".join([f"{spoken(shop.form)} of {await named(scope, shop.keeper_node_id)}" for shop in shops]))
        for tier in await session.scalars(select(SupplyTierRow).where(SupplyTierRow.market_entity_id == me.location_id).order_by(SupplyTierRow.id)):
            good = spoken(tier.commodity) if tier.commodity is not None else "all goods"
            cornered = ", cornered" if tier.cornered else ""
            found.append(
                f"the {spoken(tier.tier)} trade in {good} here is held by {await named(scope, tier.holder_node_id)} "
                f"({tier.share} in a hundred, margin {tier.margin}{cornered})"
            )
    for promotion in await session.scalars(select(PromotionRow).where(PromotionRow.holder_node_id == me.id).order_by(PromotionRow.id)):
        exposed = ", found false" if promotion.exposed else ""
        found.append(
            f"you spread word by {spoken(promotion.medium)}, reach {promotion.reach}, claims {promotion.accuracy} true{exposed}, "
            f"cost {promotion.cost} each season"
        )
    for lease in await session.scalars(select(LeaseRow).where(or_(LeaseRow.owner_node_id == me.id, LeaseRow.lessee_node_id == me.id)).order_by(LeaseRow.id)):
        side = (
            f"you lease {await named(scope, lease.thing_node_id)} to {await named(scope, lease.lessee_node_id)}"
            if lease.owner_node_id == me.id
            else (f"you rent {await named(scope, lease.thing_node_id)} from {await named(scope, lease.owner_node_id)}")
        )
        found.append(
            f"{side} for {lease.rent} each season over {several(lease.term_epochs, 'epoch', 'epochs')}; "
            f"upkeep by {spoken(lease.upkeep)}, an unpaid rent ends in {spoken(lease.on_default)}"
        )
    return found
