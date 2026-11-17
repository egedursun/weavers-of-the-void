from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_views import ViewTally, keep_views
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "settlement.population",
    "settlement.prosperity",
    "table.biology_variants",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.nodes",
    "table.people_biology",
    "table.region_environment",
    "table.settlement_profiles",
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
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.settlement_profiles",
    "table.world_type_profiles",
)
async def world_views(ctx: TickContext) -> None:
    tally = ViewTally()
    await keep_views(ctx, tally)
    count(ctx, "world_views", tally)


PHASES = (Phase("world_views", world_views),)
