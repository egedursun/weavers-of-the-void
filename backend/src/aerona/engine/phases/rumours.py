from aerona.db.profile_guard import register_profile_table
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore import rumours
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas

register_profile_table("rumours", "carrier_entity_id")


@reads(
    "belief.distortion_rate",
    "settlement.defense",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.journeys",
    "table.language_intelligibility",
    "table.language_standing",
    "table.name_registry",
    "table.nodes",
    "table.people_culture",
    "table.rumours",
    "table.skills",
    "table.speaker_cohorts",
    "table.spy_networks",
    "table.war_sides",
    "table.world_maps",
)
@writes(
    "settlement.defense",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.language_intelligibility",
    "table.legend_profiles",
    "table.memories",
    "table.name_registry",
    "table.relations",
    "table.rumours",
)
async def rumour_cycles(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    ctx.count("rumours_backfilled", await rumours.backfill(ctx, atlas))
    ctx.count("rumours_lingering", await rumours.linger(ctx))
    ctx.count("rumours_seeded", await rumours.seed(ctx, atlas))
    for channel, value in (await rumours.spread(ctx, atlas)).items():
        ctx.count(f"rumours_by_{channel}", value)
    for key, value in (await rumours.react(ctx, atlas)).items():
        ctx.count(f"rumours_{key}", value)
    ctx.count("rumours_hardened", len(await rumours.legends(ctx)))


PHASES = (Phase("rumour_cycles", rumour_cycles),)
