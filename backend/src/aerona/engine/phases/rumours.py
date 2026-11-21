from aerona.db.profile_guard import register_profile_table
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore import rumours
from aerona.engine.lore.event_names import name_happenings
from aerona.engine.lore.witnesses import choose_witnesses
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.recording.terms import explaining

register_profile_table("rumours", "carrier_entity_id")


@reads(
    "belief.distortion_rate",
    "settlement.defense",
    "table.applied_fixups",
    "table.bias_weights",
    "table.bonds",
    "table.chronicle",
    "table.creator",
    "table.dimensions",
    "table.divine_wounds",
    "table.entities",
    "table.feeling_spread",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_techniques",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.information_trust",
    "table.journeys",
    "table.language_intelligibility",
    "table.language_profiles",
    "table.language_standing",
    "table.lexemes",
    "table.minds",
    "table.name_registry",
    "table.network_nodes",
    "table.network_profiles",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.region_environment",
    "table.relationships",
    "table.reputations",
    "table.rumour_distortions",
    "table.rumours",
    "table.skills",
    "table.sons",
    "table.speaker_cohorts",
    "table.spy_networks",
    "table.stars",
    "table.taverns",
    "table.traits",
    "table.war_sides",
    "table.world_attention",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "settlement.defense",
    "table.applied_fixups",
    "table.bias_weights",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_names",
    "table.incident_participants",
    "table.incident_terms",
    "table.incidents",
    "table.information_trust",
    "table.language_intelligibility",
    "table.language_profiles",
    "table.legend_profiles",
    "table.memories",
    "table.name_registry",
    "table.node_births",
    "table.relations",
    "table.rumour_distortions",
    "table.rumours",
)
async def rumour_cycles(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    with explaining():
        ctx.count("rumours_backfilled", await rumours.backfill(ctx, atlas))
        ctx.count("rumours_lingering", await rumours.linger(ctx))
        ctx.count("witnesses_chosen", await choose_witnesses(ctx, atlas))
        ctx.count("rumours_seeded", await rumours.seed(ctx, atlas))
        for channel, value in (await rumours.spread(ctx, atlas)).items():
            ctx.count(f"rumours_by_{channel}", value)
        for key, value in (await rumours.react(ctx, atlas)).items():
            ctx.count(f"rumours_{key}", value)
        ctx.count("rumours_hardened", len(await rumours.legends(ctx)))
        ctx.count("happenings_named", await name_happenings(ctx))


PHASES = (Phase("rumour_cycles", rumour_cycles),)
