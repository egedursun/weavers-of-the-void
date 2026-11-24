from aerona.engine.context import TickContext
from aerona.engine.customs.age_sets import AgeSetTally, keep_age_sets
from aerona.engine.customs.civics import CivicsTally, keep_civics
from aerona.engine.customs.grades import backfill_duties
from aerona.engine.customs.intoxicants import IntoxicationTally, keep_intoxication
from aerona.engine.customs.marks import MarkTally, keep_marks
from aerona.engine.customs.naming import NamingTally, keep_naming
from aerona.engine.customs.revival import RevivalTally, keep_revivals
from aerona.engine.customs.time_budgets import TimeTally, keep_time_budgets
from aerona.engine.customs.town_life import TownLifeTally, keep_town_life
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


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
    "settlement.defense",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.afflictions",
    "table.age_sets",
    "table.augment_effects",
    "table.augments",
    "table.biology_variants",
    "table.body_marks",
    "table.bonds",
    "table.community_societies",
    "table.community_stocks",
    "table.conditions",
    "table.corvee_levies",
    "table.cosmopolitan_members",
    "table.creator",
    "table.cult_tenets",
    "table.culture_drift_causes",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.entity_tags",
    "table.faction_memberships",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.gatherings",
    "table.holder_levels",
    "table.holder_techniques",
    "table.hooks",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.intoxicant_customs",
    "table.item_profiles",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.lexemes",
    "table.mark_customs",
    "table.mortal_profiles",
    "table.mystics",
    "table.name_forms",
    "table.name_registry",
    "table.naming_customs",
    "table.node_births",
    "table.nodes",
    "table.notable_years",
    "table.polity_members",
    "table.prostheses",
    "table.revivals",
    "table.settlement_profiles",
    "table.sons",
    "table.species_ranges",
    "table.stars",
    "table.time_budgets",
    "table.true_names",
    "table.worlds",
)
@writes(
    "settlement.defense",
    "settlement.prosperity",
    "table.afflictions",
    "table.applied_fixups",
    "table.bodies",
    "table.body_customs",
    "table.body_marks",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.intoxicant_customs",
    "table.language_profiles",
    "table.mark_customs",
    "table.mortal_profiles",
    "table.name_forms",
    "table.naming_customs",
    "table.settlement_profiles",
    "table.species_ranges",
    "table.time_budgets",
    "table.traits",
    "table.true_names",
)
async def customs(ctx: TickContext) -> None:
    revival, intoxication, marks, time, naming, sets = RevivalTally(), IntoxicationTally(), MarkTally(), TimeTally(), NamingTally(), AgeSetTally()
    await keep_revivals(ctx, revival)
    await keep_intoxication(ctx, intoxication)
    await keep_naming(ctx, naming)
    ctx.count("grade_duties_backfilled", await backfill_duties(ctx))
    await keep_age_sets(ctx, sets)
    await keep_marks(ctx, marks)
    await keep_time_budgets(ctx, time)
    count(ctx, "revivals", revival)
    count(ctx, "intoxication", intoxication)
    count(ctx, "naming", naming)
    count(ctx, "age_sets", sets)
    count(ctx, "marks", marks)
    count(ctx, "time_budgets", time)


@reads(
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.bonds",
    "table.community_stocks",
    "table.commutes",
    "table.cooperatives",
    "table.creator",
    "table.dimensions",
    "table.districts",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.polity_profiles",
    "table.pressures",
    "table.settlement_infrastructure",
    "table.sons",
    "table.stars",
    "table.structure_profiles",
    "table.welfare_houses",
    "table.worlds",
)
@writes(
    "settlement.wealth",
    "table.chronicle",
    "table.chronicle_entities",
    "table.commutes",
    "table.cooperatives",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.mortal_profiles",
    "table.node_births",
    "table.polity_profiles",
    "table.welfare_houses",
)
async def town_life(ctx: TickContext) -> None:
    tally = TownLifeTally()
    await keep_town_life(ctx, tally)
    count(ctx, "town_life", tally)


@reads(
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.border_controls",
    "table.case_witnesses",
    "table.community_cohorts",
    "table.cosmos",
    "table.crime_cases",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.evidence",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.measure_standards",
    "table.media_items",
    "table.media_outlets",
    "table.membership_categories",
    "table.memberships",
    "table.mortal_profiles",
    "table.natural_law_profiles",
    "table.node_births",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.poor_relief",
    "table.pressures",
    "table.settlement_profiles",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.wars",
    "table.worlds",
)
@writes(
    "table.applied_fixups",
    "table.border_controls",
    "table.chronicle",
    "table.chronicle_entities",
    "table.crime_cases",
    "table.evidence",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.measure_standards",
    "table.membership_categories",
    "table.memberships",
    "table.oaths",
    "table.polity_profiles",
    "table.poor_relief",
    "table.settlement_profiles",
)
async def civics(ctx: TickContext) -> None:
    tally = CivicsTally()
    await keep_civics(ctx, tally)
    count(ctx, "civics", tally)


PHASES = (
    Phase("customs", customs),
    Phase("town_life", town_life),
    Phase("civics", civics),
)
