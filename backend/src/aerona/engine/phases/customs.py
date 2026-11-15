from aerona.engine.context import TickContext
from aerona.engine.customs.age_sets import AgeSetTally, keep_age_sets
from aerona.engine.customs.civics import CivicsTally, keep_civics
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
    "settlement.defense",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.age_sets",
    "table.body_marks",
    "table.bonds",
    "table.community_societies",
    "table.community_stocks",
    "table.cosmopolitan_members",
    "table.culture_drift_causes",
    "table.epoch_year_cursors",
    "table.gatherings",
    "table.hooks",
    "table.intoxicant_customs",
    "table.language_profiles",
    "table.lexemes",
    "table.mark_customs",
    "table.mortal_profiles",
    "table.name_forms",
    "table.name_registry",
    "table.naming_customs",
    "table.revivals",
    "table.settlement_profiles",
    "table.time_budgets",
    "table.true_names",
)
@writes(
    "settlement.defense",
    "table.body_marks",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.intoxicant_customs",
    "table.language_profiles",
    "table.mark_customs",
    "table.mortal_profiles",
    "table.name_forms",
    "table.naming_customs",
    "table.settlement_profiles",
    "table.time_budgets",
    "table.true_names",
)
async def customs(ctx: TickContext) -> None:
    revival, intoxication, marks, time, naming, sets = RevivalTally(), IntoxicationTally(), MarkTally(), TimeTally(), NamingTally(), AgeSetTally()
    await keep_revivals(ctx, revival)
    await keep_intoxication(ctx, intoxication)
    await keep_naming(ctx, naming)
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
    "settlement.prosperity",
    "table.bonds",
    "table.community_stocks",
    "table.commutes",
    "table.cooperatives",
    "table.districts",
    "table.epoch_year_cursors",
    "table.pressures",
    "table.settlement_infrastructure",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.commutes",
    "table.cooperatives",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
)
async def town_life(ctx: TickContext) -> None:
    tally = TownLifeTally()
    await keep_town_life(ctx, tally)
    count(ctx, "town_life", tally)


@reads(
    "table.border_controls",
    "table.case_witnesses",
    "table.crime_cases",
    "table.evidence",
    "table.measure_standards",
    "table.membership_categories",
    "table.memberships",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.poor_relief",
    "table.pressures",
    "table.wars",
)
@writes(
    "table.border_controls",
    "table.crime_cases",
    "table.evidence",
    "table.measure_standards",
    "table.membership_categories",
    "table.memberships",
    "table.polity_profiles",
    "table.poor_relief",
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
