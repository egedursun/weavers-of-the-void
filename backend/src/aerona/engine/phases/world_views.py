from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_views import ViewTally, keep_views
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.settlement.modes import ModeTally, keep_modes


@reads(
    "settlement.population",
    "settlement.prosperity",
    "table.biology_variants",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.node_births",
    "table.nodes",
    "table.people_biology",
    "table.region_environment",
    "table.settlement_profiles",
    "table.sons",
    "table.stars",
    "table.water_lifts",
    "table.world_type_profiles",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_stocks",
    "table.entities",
    "table.goods_flows",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.settlement_profiles",
    "table.world_type_profiles",
)
async def world_views(ctx: TickContext) -> None:
    tally = ViewTally()
    await keep_views(ctx, tally)
    count(ctx, "world_views", tally)


@reads(
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.bonds",
    "table.calendars",
    "table.entities",
    "table.forced_weather",
    "table.irregular_seasons",
    "table.nodes",
    "table.people_biology",
    "table.place_environment",
    "table.region_environment",
    "table.settlement_profiles",
    "table.sky_events",
    "table.stars",
    "table.world_seasons",
    "table.world_type_profiles",
    "table.worlds",
)
@writes(
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.settlement_profiles",
)
async def settle_modes(ctx: TickContext) -> None:
    tally = ModeTally()
    await keep_modes(ctx, tally)
    ctx.count("settle_modes_set", tally.settled)
    ctx.count("settle_modes_weathered", tally.weathered)
    ctx.count("settle_modes_fell", tally.fell)
    ctx.count("settle_modes_unfit", tally.unfit)


PHASES = (Phase("world_views", world_views), Phase("settle_modes", settle_modes))
