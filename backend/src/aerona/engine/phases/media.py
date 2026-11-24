from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.media.press import keep_media
from aerona.engine.media.seed import seed_media
from aerona.engine.phase import Phase


@reads(
    "table.bonds",
    "table.entities",
    "table.incidents",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.media_items",
    "table.media_outlets",
    "table.mortal_profiles",
    "table.nodes",
    "table.polity_members",
    "table.polity_profiles",
    "table.public_opinion",
    "table.record_media",
    "table.settlement_profiles",
    "table.structure_profiles",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.media_items",
    "table.media_outlets",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.public_opinion",
    "table.record_media",
    "table.settlement_profiles",
)
async def media(ctx: TickContext) -> None:
    ctx.count("media_seeded", await seed_media(ctx))
    tally = await keep_media(ctx)
    ctx.count("media_published", tally.published)
    ctx.count("media_exposed", tally.exposed)
    ctx.count("media_decayed", tally.decayed)
    ctx.count("media_found", tally.found)
    ctx.count("media_stars", tally.stars)
    ctx.count("media_censored", tally.censored)
    ctx.count("media_swayed", tally.swayed)


PHASES = (Phase("media", media),)
