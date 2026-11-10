from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import COMMUNITY_TYPES
from aerona.engine.context import TickContext
from aerona.engine.divine.standing import standing_row
from aerona.engine.dominion.book import DominionBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int


async def blame_rulers(ctx: TickContext, struck_ids: list[int]) -> int:
    table = ctx.rules.dominion
    atlas = await RegionAtlas.load(ctx.session)
    book = await DominionBook.load(ctx.session)
    blamed = 0
    for community_id in sorted(set(struck_ids)):
        community = await ctx.session.get(EntityRow, community_id)
        ruler = book.ruler(ctx.rules, atlas.top_region(community_id))
        if community is None or community.entity_type not in COMMUNITY_TYPES or ruler is None or held(community_id, ruler):
            continue
        standing = await standing_row(ctx, community_id, ruler)
        if "fear" not in standing.locked:
            standing.fear = clamp_int(standing.fear + table.blame_fear, 0, PERCENT)
        if "love" not in standing.locked:
            standing.love = clamp_int(standing.love - table.blame_love, 0, PERCENT)
        blamed += 1
    return blamed
