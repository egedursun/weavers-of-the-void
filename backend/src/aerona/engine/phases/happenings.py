from aerona.engine.context import TickContext
from aerona.engine.environment.geomorph import reshape
from aerona.engine.happenings.backfill import backfill_casualties
from aerona.engine.happenings.emergence import emerge
from aerona.engine.happenings.progression import advance, ensure_profiles, link_profiles, siege_events
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas


@reads(
    "table.entities",
    "table.epoch_year_cursors",
    "table.event_footprints",
    "table.incident_participants",
    "table.incidents",
    "table.nodes",
    "table.region_environment",
    "table.region_geomorphology",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.region_environment",
    "table.region_geomorphology",
)
async def geomorphology(ctx: TickContext) -> None:
    for key, value in sorted((await reshape(ctx)).items()):
        ctx.count(f"land_{key}", value)


@reads(
    "cult.influence",
    "cult.zeal",
    "event.severity",
    "people.piety",
    "people.population",
    "people.prosperity",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.battles",
    "table.bonds",
    "table.community_cohorts",
    "table.community_relations",
    "table.cosmos",
    "table.entities",
    "table.epoch_year_cursors",
    "table.event_casualties",
    "table.event_footprints",
    "table.event_profiles",
    "table.heresies",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.name_registry",
    "table.nodes",
    "table.outbreaks",
    "table.region_environment",
    "table.settlement_profiles",
    "table.settlement_treasury",
    "table.sieges",
    "table.sky_events",
    "table.world_maps",
    "table.world_seasons",
)
@writes(
    "cult.influence",
    "cult.zeal",
    "people.piety",
    "people.population",
    "people.prosperity",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.epoch_year_cursors",
    "table.event_casualties",
    "table.event_footprints",
    "table.event_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.name_registry",
    "table.region_environment",
    "table.settlement_profiles",
)
async def event_phases(ctx: TickContext) -> None:
    ctx.count("event_casualties_backfilled", await backfill_casualties(ctx))
    atlas = await RegionAtlas.load(ctx.session)
    for key, value in sorted((await ensure_profiles(ctx, atlas)).items()):
        ctx.count(f"event_profiles_{key}", value)
    ctx.count("event_links", await link_profiles(ctx))
    for key, value in sorted((await emerge(ctx, atlas)).items()):
        ctx.count(f"events_{key}", value)
    ctx.count("siege_events", await siege_events(ctx, atlas))
    for key, value in sorted((await advance(ctx, atlas)).items()):
        ctx.count(f"event_phase_{key}", value)


PHASES = (Phase("geomorphology", geomorphology), Phase("event_phases", event_phases))
