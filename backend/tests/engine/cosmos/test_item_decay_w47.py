from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.context import TickContext
from aerona.engine.phases.production import _decay_item
from tests.engine.cosmos.factories import Cosmos, make_entity


async def test_an_item_with_nothing_to_wear_away_outlasts_decay(ctx: TickContext, cosmos: Cosmos) -> None:
    keepsake = await make_entity(ctx.session, "Keepsake", EntityType.ITEM, ItemStats(curse=40), world_id=cosmos.home.id)
    assert await _decay_item(ctx, keepsake, 5, 100, 0) is False
    assert keepsake.status is EntityStatus.CANON


async def test_an_item_whose_worth_wears_to_nothing_crumbles(ctx: TickContext, cosmos: Cosmos) -> None:
    blade = await make_entity(ctx.session, "Blade", EntityType.ITEM, ItemStats(damage=3), world_id=cosmos.home.id)
    assert await _decay_item(ctx, blade, 5, 100, 0) is True
    assert blade.status is EntityStatus.DESTROYED
