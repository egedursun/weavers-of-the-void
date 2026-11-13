from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.structures.backfill import backfill_structures
from aerona.engine.structures.functions import run_functions
from aerona.engine.structures.types import type_standing
from aerona.engine.structures.upkeep import upkeep_all


@reads(
    "structure.durability",
    "table.applied_fixups",
    "table.bonds",
    "table.community_cohorts",
    "table.entity_flags",
    "table.node_materials",
    "table.nodes",
    "table.people_culture",
    "table.sons",
    "table.structure_designs",
    "table.structure_profiles",
    "table.structure_staff",
    "table.workshops",
    "table.world_materials",
)
@writes("structure.durability", "table.applied_fixups", "table.entities", "table.structure_profiles", "table.structure_staff", "table.workshops")
async def structure_survey(ctx: TickContext) -> None:
    result = await backfill_structures(ctx)
    for key, value in result.items():
        ctx.count(key, value)
    ctx.count("structures_typed", await type_standing(ctx))


@reads(
    "structure.durability",
    "structure.function",
    "table.community_cohorts",
    "table.community_stocks",
    "table.node_materials",
    "table.nodes",
    "table.settlement_profiles",
    "table.structure_designs",
    "table.structure_profiles",
    "table.structure_sections",
    "table.structure_staff",
    "table.workshops",
    "table.world_materials",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_stocks",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.settlement_profiles",
    "table.settlement_treasury",
    "table.structure_profiles",
    "table.structure_staff",
    "table.workshops",
)
async def structure_upkeep(ctx: TickContext) -> None:
    ctx.count("kept", await upkeep_all(ctx))


@reads(
    "people.piety",
    "people.prosperity",
    "people.wealth",
    "settlement.defense",
    "settlement.piety",
    "settlement.prosperity",
    "settlement.wealth",
    "table.bonds",
    "table.people_culture",
    "table.skills",
    "table.sons",
    "table.structure_profiles",
)
@writes(
    "knowledge.spread",
    "people.piety",
    "people.prosperity",
    "people.wealth",
    "settlement.defense",
    "settlement.piety",
    "settlement.prosperity",
    "settlement.wealth",
    "table.bodies",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.people_culture",
    "table.skills",
    "table.sons",
)
async def structure_functions(ctx: TickContext) -> None:
    tally = await run_functions(ctx)
    ctx.count("knowledge_deepened", tally.deepened)
    ctx.count("functions", tally.held)
    ctx.count("duels", tally.duels)


SURVEY_PHASES = (Phase("structure_survey", structure_survey),)
UPKEEP_PHASES = (Phase("structure_upkeep", structure_upkeep),)
FUNCTION_PHASES = (Phase("structure_functions", structure_functions),)
PHASES = SURVEY_PHASES + UPKEEP_PHASES + FUNCTION_PHASES
