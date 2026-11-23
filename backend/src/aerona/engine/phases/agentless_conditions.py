from dataclasses import asdict

from aerona.engine.agentless_conditions.arise import ConditionTally, roll_conditions
from aerona.engine.agentless_conditions.catalogue import seed_catalogue
from aerona.engine.agentless_conditions.course import tend_courses
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "mortal.willpower",
    "people.prosperity",
    "settlement.prosperity",
    "table.agentless_conditions",
    "table.augment_effects",
    "table.augments",
    "table.body_systems",
    "table.bonds",
    "table.conditions",
    "table.cult_tenets",
    "table.culture_values",
    "table.entities",
    "table.entity_tags",
    "table.folk_knowledge",
    "table.holder_levels",
    "table.injuries",
    "table.item_profiles",
    "table.mind_facets",
    "table.mind_profiles",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.prostheses",
    "table.region_pollution",
    "table.thoughts",
    "table.worlds",
)
@writes(
    "mortal.lifespan",
    "table.agentless_conditions",
    "table.applied_fixups",
    "table.bodies",
    "table.body_customs",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.thoughts",
)
async def agentless_conditions(ctx: TickContext) -> None:
    tally = ConditionTally(seeded=await seed_catalogue(ctx))
    await tend_courses(ctx, tally)
    await roll_conditions(ctx, tally)
    for key, value in asdict(tally).items():
        ctx.count(f"conditions_{key}", value)


PHASES = (Phase("agentless_conditions", agentless_conditions),)
