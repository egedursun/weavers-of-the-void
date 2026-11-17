from aerona.engine.context import TickContext
from aerona.engine.folkways.biases import BiasTally, keep_biases
from aerona.engine.folkways.mishaps import MishapTally, keep_mishaps
from aerona.engine.folkways.nutrition import NutritionTally, keep_nutrition
from aerona.engine.folkways.purity import PurityTally, keep_purity
from aerona.engine.folkways.witchcraft import WitchTally, keep_witchcraft
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.assistive_aids",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.community_stocks",
    "table.conditions",
    "table.cult_tenets",
    "table.culture_values",
    "table.custom_kinds",
    "table.diets",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.famine_lore",
    "table.genomes",
    "table.holder_custom_techniques",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.irregular_seasons",
    "table.item_profiles",
    "table.mind_attributes",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.natural_law_profiles",
    "table.nodes",
    "table.nutrient_needs",
    "table.nutrition_scores",
    "table.pressures",
    "table.prostheses",
    "table.technology_profiles",
    "table.thoughts",
    "table.tradition_profiles",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "mortal.endurance",
    "mortal.intellect",
    "mortal.strength",
    "table.bodies",
    "table.body_customs",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.diets",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.mind_attributes",
    "table.mortal_profiles",
    "table.nutrient_needs",
    "table.nutrition_scores",
    "table.thoughts",
)
async def nutrition(ctx: TickContext) -> None:
    tally = NutritionTally()
    await keep_nutrition(ctx, tally)
    count(ctx, "nutrition", tally)


@reads(
    "table.bias_weights", "table.biology_variants", "table.bonds", "table.entities", "table.foreign_gods", "table.mortal_profiles", "table.nodes", "table.sons"
)
@writes("table.bias_weights")
async def biases(ctx: TickContext) -> None:
    tally = BiasTally()
    await keep_biases(ctx, tally)
    count(ctx, "biases", tally)


@reads("table.culture_values", "table.districts", "table.entities", "table.impurity_sources", "table.nodes", "table.purity_ranks")
@writes("table.impurity_sources", "table.purity", "table.purity_ranks")
async def purity(ctx: TickContext) -> None:
    tally = PurityTally()
    await keep_purity(ctx, tally)
    count(ctx, "purity", tally)


@reads(
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.augment_effects",
    "table.augments",
    "table.avatars",
    "table.bodies",
    "table.bonds",
    "table.castings",
    "table.charms",
    "table.conditions",
    "table.cult_tenets",
    "table.culture_values",
    "table.divine_wounds",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.foreign_gods",
    "table.fortune_laws",
    "table.fortune_profiles",
    "table.games",
    "table.goods_flows",
    "table.hidden_truths",
    "table.holder_levels",
    "table.impurity_sources",
    "table.incident_participants",
    "table.incidents",
    "table.incubating_ideas",
    "table.injuries",
    "table.insurance_policies",
    "table.insurers",
    "table.item_profiles",
    "table.kind_holdings",
    "table.luck_beliefs",
    "table.marriages",
    "table.memories",
    "table.mind_attributes",
    "table.mind_profiles",
    "table.mishaps",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.nodes",
    "table.notable_years",
    "table.outbreaks",
    "table.passions",
    "table.prostheses",
    "table.routes",
    "table.sons",
    "table.tradition_profiles",
    "table.war_sides",
    "table.world_domain_hooks",
)
@writes(
    "mortal.death_year",
    "mortal.hp",
    "mortal.lifespan",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.injuries",
    "table.marriages",
    "table.memories",
    "table.mishaps",
    "table.mortal_profiles",
    "table.sons",
)
async def mishaps(ctx: TickContext) -> None:
    tally = MishapTally()
    await keep_mishaps(ctx, tally)
    count(ctx, "mishaps", tally)


@reads(
    "table.accusations",
    "table.beliefs",
    "table.castings",
    "table.chronicle_entities",
    "table.divination_systems",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.memories",
    "table.mishaps",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.relationships",
    "table.rumours",
    "table.traits",
    "table.witch_hunts",
)
@writes(
    "table.accusations",
    "table.chronicle",
    "table.chronicle_entities",
    "table.crime_cases",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
)
async def witchcraft(ctx: TickContext) -> None:
    tally = WitchTally()
    await keep_witchcraft(ctx, tally)
    count(ctx, "witchcraft", tally)


PHASES = (
    Phase("nutrition", nutrition),
    Phase("biases", biases),
    Phase("purity", purity),
    Phase("mishaps", mishaps),
    Phase("witchcraft", witchcraft),
)
