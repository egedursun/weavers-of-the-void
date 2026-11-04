from aerona.engine.context import TickContext
from aerona.engine.cosmos.foreign_gods import birth_local_gods
from aerona.engine.cosmos.maps import refresh_world_maps
from aerona.engine.cosmos.stars import choose_epoch_stars
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads("table.world_maps")
@writes("table.entities", "table.world_maps")
async def world_maps(ctx: TickContext) -> None:
    for refresh in await refresh_world_maps(ctx.session, ctx.rules, ctx.epoch):
        ctx.count("maps_drawn")
        ctx.count("map_regions", refresh.regions)


@reads("celestial.brightness")
@writes("table.worlds")
async def epoch_stars(ctx: TickContext) -> None:
    chosen = await choose_epoch_stars(ctx)
    ctx.count("stars_chosen", sum(1 for star in chosen.values() if star is not None))


@reads("table.entities", "table.foreign_gods", "table.worlds")
@writes("table.chronicle", "table.foreign_gods", "table.incidents")
async def local_gods(ctx: TickContext) -> None:
    ctx.count("born", len(await birth_local_gods(ctx)))


MAP_PHASES = (Phase("world_maps", world_maps),)
STAR_PHASES = (Phase("epoch_stars", epoch_stars),)
LOCAL_GOD_PHASES = (Phase("local_gods", local_gods),)
PHASES = MAP_PHASES + STAR_PHASES + LOCAL_GOD_PHASES
