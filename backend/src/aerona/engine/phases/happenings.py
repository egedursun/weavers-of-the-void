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
    "table.event_footprints",
    "table.incident_participants",
    "table.incidents",
    "table.nodes",
    "table.region_environment",
    "table.region_geomorphology",
    "table.worlds",
)
@writes(
    "table.chronicle", "table.chronicle_entities", "table.incident_participants", "table.incidents", "table.region_environment", "table.region_geomorphology"
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
    "table.creator",
    "table.culture_values",
    "table.deep_passages",
    "table.dimensions",
    "table.entities",
    "table.event_casualties",
    "table.event_footprints",
    "table.event_profiles",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.held_identities",
    "table.heresies",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.personality_values",
    "table.region_environment",
    "table.relationships",
    "table.reputations",
    "table.role_norms",
    "table.ruler_currencies",
    "table.settlement_profiles",
    "table.settlement_treasury",
    "table.sieges",
    "table.sky_events",
    "table.sons",
    "table.speaker_cohorts",
    "table.stars",
    "table.traits",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
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
    "table.event_casualties",
    "table.event_footprints",
    "table.event_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
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
