from aerona.engine.context import TickContext
from aerona.engine.endowments.seed import seed_endowments
from aerona.engine.endowments.trust import EndowmentTally, keep_endowments
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "settlement.piety",
    "settlement.prosperity",
    "table.bonds",
    "table.endowments",
    "table.entities",
    "table.folk_knowledge",
    "table.mortal_profiles",
    "table.nodes",
    "table.number_systems",
    "table.polity_members",
    "table.polity_profiles",
    "table.settlement_profiles",
    "table.welfare_houses",
)
@writes(
    "settlement.piety",
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.endowments",
    "table.folk_knowledge",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.mortal_profiles",
    "table.number_systems",
    "table.polity_profiles",
    "table.settlement_profiles",
)
async def endowments(ctx: TickContext) -> None:
    tally = EndowmentTally(seeded=await seed_endowments(ctx))
    await keep_endowments(ctx, tally)
    ctx.count("endowments_seeded", tally.seeded)
    ctx.count("endowments_paid", tally.paid)
    ctx.count("endowments_skimmed", tally.skimmed)
    ctx.count("endowments_captured", tally.captured)
    ctx.count("endowments_confiscated", tally.confiscated)
    ctx.count("endowments_ended", tally.ended)
    ctx.count("endowments_outlived", tally.outlived)


PHASES = (Phase("endowments", endowments),)
