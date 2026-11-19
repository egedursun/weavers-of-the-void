from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.speech.oratory import keep_speech
from aerona.engine.speech.seed import seed_humour


@reads(
    "mortal.charisma",
    "settlement.piety",
    "table.bonds",
    "table.creator",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.humour_styles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.media_outlets",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.settlement_profiles",
    "table.sons",
    "table.speeches",
    "table.stars",
    "table.worlds",
)
@writes(
    "settlement.piety",
    "table.chronicle",
    "table.chronicle_entities",
    "table.humour_styles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.settlement_profiles",
    "table.speeches",
)
async def speech(ctx: TickContext) -> None:
    ctx.count("speech_seeded", await seed_humour(ctx))
    tally = await keep_speech(ctx)
    ctx.count("speech_heard", tally.heard)
    ctx.count("speech_votes", tally.votes)
    ctx.count("speech_crowds", tally.crowds)
    ctx.count("speech_offended", tally.offended)
    ctx.count("speech_punished", tally.punished)
    ctx.count("speech_satire", tally.satire)
    ctx.count("speech_rallied", tally.rallied)


PHASES = (Phase("speech", speech),)
