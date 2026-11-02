from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.rules.registry import Rules


def default_class_shares(rules: Rules) -> dict[SocialClass, float]:
    society = rules.society
    return {
        SocialClass.FARMER: float(society.class_farmer_pct),
        SocialClass.ARTISAN: float(society.class_artisan_pct),
        SocialClass.MERCHANT: float(society.class_merchant_pct),
        SocialClass.PRIEST: float(society.class_priest_pct),
        SocialClass.WARRIOR: float(society.class_warrior_pct),
        SocialClass.SCRIBE: float(society.class_scribe_pct),
    }


async def class_shares(session: AsyncSession, rules: Rules, entity_id: int) -> dict[SocialClass, float]:
    row = await session.get(CommunitySocietyRow, entity_id)
    if row is None:
        return default_class_shares(rules)
    return {social_class: row.share(social_class) for social_class in SocialClass}


async def stock(session: AsyncSession, rules: Rules, entity_id: int, commodity: Commodity) -> int:
    row = await session.get(CommunitySocietyRow, entity_id)
    if row is not None:
        return row.stock(commodity)
    defaults = {Commodity.FOOD: rules.society.initial_food, Commodity.ORE: rules.society.initial_ore, Commodity.GOODS: rules.society.initial_goods}
    return defaults[commodity]


async def set_stock(session: AsyncSession, entity_id: int, commodity: Commodity, value: int) -> bool:
    row = await session.get(CommunitySocietyRow, entity_id)
    if row is None:
        return False
    setattr(row, f"stock_{commodity.value}", max(0, value))
    return True
