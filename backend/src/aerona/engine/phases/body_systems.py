from aerona.engine.body.systems import BodySystemTally, keep_body_systems
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "settlement.prosperity",
    "table.augments",
    "table.biology_variants",
    "table.body_systems",
    "table.community_stocks",
    "table.entities",
    "table.garment_kinds",
    "table.kind_holdings",
    "table.node_births",
    "table.nodes",
    "table.powers",
    "table.region_environment",
    "table.rite_grammar",
    "table.sensitivities",
    "table.species_profiles",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "table.body_systems",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
)
async def body_systems(ctx: TickContext) -> None:
    tally = BodySystemTally()
    await keep_body_systems(ctx, tally)
    ctx.count("body_systems_seeded", tally.seeded)
    ctx.count("body_systems_strained", tally.strained)
    ctx.count("body_systems_failed", tally.failed)
    ctx.count("body_systems_recovered", tally.recovered)
    ctx.count("body_systems_adapted", tally.adapted)
    ctx.count("body_sensitivity_reactions", tally.reactions)


PHASES = (Phase("body_systems", body_systems),)
