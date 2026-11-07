from sqlalchemy import select

from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import TerrainKind
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.deposits import Deposit, open_deposit

COAL_TERRAINS_BLOCKED = frozenset({TerrainKind.ICE_SHEET, TerrainKind.VOLCANIC, TerrainKind.VOID_SHORE, TerrainKind.FLESH, TerrainKind.CRYSTAL_FIELD})


async def lay_coal_seams(ctx: TickContext, book: EconomyBook) -> int:
    table = ctx.rules.mines
    coal = select(ResourceProfileRow.resource_entity_id).where(ResourceProfileRow.commodity == CommodityKind.COAL)
    seamed = {book.ground.atlas.top_region(resource_id) for resource_id in await ctx.session.scalars(coal)}
    laid = 0
    for region in sorted(book.ground.regions.values(), key=lambda row: row.entity_id):
        place = book.entities.get(region.entity_id)
        if place is None or place.is_water or held(region.entity_id) or region.entity_id in seamed or region.base_forest < table.coal_forest_at:
            continue
        if region.dominant_terrain in COAL_TERRAINS_BLOCKED or not ctx.rng(f"coal_seam.{region.entity_id}").chance(table.coal_seam_pct):
            continue
        depth = (region.base_forest + region.base_wetland) // 2
        await open_deposit(
            ctx,
            Deposit(
                name=f"Coal Measures of {place.name}",
                body=f"Black seams of coal, the buried forests of long ago, lie under {place.name}.",
                place=place,
                commodity=CommodityKind.COAL,
                richness=max(20, depth),
                quality=max(20, depth),
                revealed=False,
            ),
        )
        laid += 1
    return laid
