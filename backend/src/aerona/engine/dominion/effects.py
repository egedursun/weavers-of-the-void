from aerona.domain.enums.dominion import DivineScale
from aerona.engine.context import TickContext
from aerona.engine.dominion.book import DominionBook
from aerona.engine.primitives.distance import RegionAtlas


async def scale_here(ctx: TickContext, entity_id: int, scale: DivineScale) -> int:
    atlas = await RegionAtlas.load(ctx.session)
    return (await DominionBook.load(ctx.session)).scale_at(ctx.rules, atlas.top_region(entity_id), scale)


async def step_here(ctx: TickContext, entity_id: int, scale: DivineScale, pct: int) -> float:
    atlas = await RegionAtlas.load(ctx.session)
    return (await DominionBook.load(ctx.session)).step_factor(ctx.rules, atlas.top_region(entity_id), scale, pct)


async def divine_power(ctx: TickContext, god_id: int | None, entity_id: int, pct: int) -> float:
    atlas = await RegionAtlas.load(ctx.session)
    book = await DominionBook.load(ctx.session)
    return book.power_factor(ctx.rules, god_id, atlas.top_region(entity_id), pct) * book.aptitude_factor(ctx.rules, god_id)
