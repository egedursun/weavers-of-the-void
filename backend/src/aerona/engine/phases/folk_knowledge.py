from aerona.engine.context import TickContext
from aerona.engine.folk_knowledge.lore import FolkTally, keep_folk_knowledge
from aerona.engine.folk_knowledge.seed import seed_folk_knowledge
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "mortal.hp",
    "settlement.piety",
    "table.bonds",
    "table.celestial_readings",
    "table.creator",
    "table.culture_values",
    "table.deep_passages",
    "table.dimensions",
    "table.disease_profiles",
    "table.entities",
    "table.folk_classes",
    "table.folk_knowledge",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_techniques",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.number_systems",
    "table.polity_members",
    "table.region_environment",
    "table.settlement_profiles",
    "table.sons",
    "table.species_products",
    "table.species_profiles",
    "table.stars",
    "table.theory_adherents",
    "table.theory_profiles",
    "table.world_materials",
    "table.worlds",
)
@writes(
    "mortal.hp",
    "settlement.piety",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.folk_classes",
    "table.folk_knowledge",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.mortal_profiles",
    "table.number_systems",
    "table.settlement_profiles",
)
async def folk_knowledge(ctx: TickContext) -> None:
    tally = FolkTally(seeded=await seed_folk_knowledge(ctx))
    await keep_folk_knowledge(ctx, tally)
    ctx.count("folk_seeded", tally.seeded)
    ctx.count("folk_learned", tally.learned)
    ctx.count("folk_corrected", tally.corrected)
    ctx.count("folk_harmed", tally.harmed)
    ctx.count("folk_exchanged", tally.exchanged)
    ctx.count("folk_pulled", tally.pulled)
    ctx.count("folk_schooled", tally.schooled)
    ctx.count("folk_lost", tally.lost)
    ctx.count("folk_read", tally.read)


PHASES = (Phase("folk_knowledge", folk_knowledge),)
