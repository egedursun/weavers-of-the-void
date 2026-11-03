from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.engine.economy.stocks import goods_of
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
        SocialClass.NOBLE: float(society.class_noble_pct),
        SocialClass.SERF_OR_SLAVE: float(society.class_serf_pct),
        SocialClass.OUTCAST: float(society.class_outcast_pct),
        SocialClass.MONASTIC: float(society.class_monastic_pct),
    }


async def class_shares(session: AsyncSession, rules: Rules, entity_id: int) -> dict[SocialClass, float]:
    row = await session.get(CommunitySocietyRow, entity_id)
    if row is None:
        return default_class_shares(rules)
    return {social_class: row.share(social_class) for social_class in SocialClass}


async def supply_index(session: AsyncSession, entity_id: int, commodity: Commodity) -> int | None:
    row = await session.get(CommunitySocietyRow, entity_id)
    return row.stock(commodity) if row is not None else None


async def stock(session: AsyncSession, rules: Rules, entity_id: int, commodity: Commodity) -> int:
    row = await session.get(CommunitySocietyRow, entity_id)
    if row is not None:
        return row.stock(commodity)
    defaults = {Commodity.FOOD: rules.society.initial_food, Commodity.ORE: rules.society.initial_ore, Commodity.GOODS: rules.society.initial_goods}
    return defaults[commodity]


async def shift_stock(session: AsyncSession, rules: Rules, entity_id: int, commodity: Commodity, delta: int, *, epoch: int, flow: GoodsFlow) -> bool:
    row = await session.get(CommunitySocietyRow, entity_id)
    entity = await session.get(EntityRow, entity_id)
    if row is None or entity is None:
        return False
    await goods_of(session, epoch).shift_aggregate(rules, entity, commodity, delta, flow=flow)
    return True


async def move_stock(
    session: AsyncSession, rules: Rules, source_id: int, target_id: int, commodity: Commodity, *, index: int, epoch: int, flow: GoodsFlow
) -> int:
    source, target = await session.get(EntityRow, source_id), await session.get(EntityRow, target_id)
    if source is None or target is None or await session.get(CommunitySocietyRow, target_id) is None:
        return 0
    return await goods_of(session, epoch).move_aggregate(rules, source, target, commodity, index=index, flow=flow)
