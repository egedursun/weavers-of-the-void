from sqlalchemy import select

from aerona.db.tables.celestial import StarRow
from aerona.db.write_guard import held
from aerona.engine.context import TickContext
from aerona.engine.cosmos.beings import being_cycles
from aerona.engine.cosmos.climate import regional_climate
from aerona.engine.cosmos.commerce import cosmic_trade
from aerona.engine.cosmos.dimensions import dimension_cycles
from aerona.engine.cosmos.galaxies import galaxy_cycles
from aerona.engine.cosmos.influence import cosmic_influence, signature_minerals
from aerona.engine.cosmos.ladder import ensure_ladder, place_free_worlds, settle_star
from aerona.engine.cosmos.omens import celestial_omens
from aerona.engine.cosmos.phenomena import phenomena_cycles
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.rifts import rift_cycles
from aerona.engine.cosmos.starlife import star_lives
from aerona.engine.cosmos.strata import host_strata_once
from aerona.engine.cosmos.worldlife import regional_leak, world_lives
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases import physics


@reads("table.afterlife_strata", "table.applied_fixups", "table.cosmos", "table.dimensional_events", "table.galactic_structures", "table.name_registry")
@writes(
    "table.afterlife_strata",
    "table.applied_fixups",
    "table.dimensions",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.name_registry",
    "table.stars",
)
async def scale_ladder(ctx: TickContext) -> None:
    ctx.count("stars_placed", await ensure_ladder(ctx.session, ctx.rules))
    ctx.count("free_worlds_placed", await place_free_worlds(ctx.session))
    ctx.count("strata_hosted", await host_strata_once(ctx.session))
    cosmography = await Cosmography.load(ctx.session)
    for star in await ctx.session.scalars(select(StarRow).order_by(StarRow.id)):
        if not held(star.id):
            settle_star(ctx.rules, cosmography, star)
    await ctx.session.flush()


@reads("table.cosmos", "table.dimensional_events", "table.galactic_structures", "table.modifiers", "table.region_environment", "table.rifts")
@writes("table.region_environment")
async def influence(ctx: TickContext) -> None:
    ctx.count("cosmic_modifiers", await cosmic_influence(ctx))
    ctx.count("signature_minerals", await signature_minerals(ctx))


@reads(
    "settlement.population",
    "table.bonds",
    "table.community_stocks",
    "table.cosmos",
    "table.dimensional_events",
    "table.galactic_structures",
    "table.goods_flows",
    "table.holder_techniques",
    "table.law_jurisdictions",
    "table.polity_members",
    "table.polity_profiles",
    "table.routes",
)
@writes("table.community_stocks", "table.goods_flows", "table.routes")
async def trade(ctx: TickContext) -> None:
    ctx.count("goods_carried", await cosmic_trade(ctx))


@reads("table.entity_flags", "table.region_environment", "table.rifts", "table.routes")
@writes("table.region_environment")
async def leak_by_region(ctx: TickContext) -> None:
    ctx.count("hot_regions", await regional_leak(ctx))


@reads("table.region_environment", "table.world_cycles", "table.world_maps")
@writes("table.region_environment")
async def climate_by_region(ctx: TickContext) -> None:
    ctx.count("climate_shifts", await regional_climate(ctx))


PHASES = (
    Phase("scale_ladder", scale_ladder),
    *physics.EARLY,
    Phase("cosmic_influence", influence),
    Phase("galaxy_cycles", galaxy_cycles),
    Phase("star_lives", star_lives),
    *physics.LATE,
    Phase("dimension_cycles", dimension_cycles),
    Phase("rift_cycles", rift_cycles),
    Phase("cosmic_beings", being_cycles),
    Phase("phenomena", phenomena_cycles),
    Phase("regional_leak", leak_by_region),
    Phase("celestial_omens", celestial_omens),
    Phase("cosmic_trade", trade),
    Phase("world_lives", world_lives),
    Phase("regional_climate", climate_by_region),
)
