from sqlalchemy import select

from aerona.db.tables.households import HouseholdRow
from aerona.engine.context import TickContext
from aerona.engine.households.formation import house_everyone
from aerona.engine.households.life import HouseholdTally, tend_aggregates, tend_household
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.polity.laws import LawBook


@reads(
    "settlement.population",
    "table.bonds",
    "table.districts",
    "table.dwellings",
    "table.household_members",
    "table.households",
    "table.mortal_profiles",
    "table.offices",
    "table.place_profiles",
)
@writes("table.dwellings", "table.household_members", "table.households")
async def household_survey(ctx: TickContext) -> None:
    ctx.count("households_housed", await house_everyone(ctx))


@reads(
    "mortal.age",
    "people.prosperity",
    "settlement.prosperity",
    "table.bonds",
    "table.community_cohorts",
    "table.culture_ethics",
    "table.culture_values",
    "table.districts",
    "table.dwelling_furnishings",
    "table.dwellings",
    "table.epoch_year_cursors",
    "table.house_members",
    "table.house_profiles",
    "table.household_aggregates",
    "table.household_members",
    "table.households",
    "table.injuries",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.offices",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.site_profits",
    "table.thoughts",
    "table.tradition_profiles",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.dwelling_furnishings",
    "table.dwellings",
    "table.entities",
    "table.epoch_year_cursors",
    "table.house_profiles",
    "table.household_aggregates",
    "table.household_members",
    "table.households",
    "table.incident_participants",
    "table.incidents",
    "table.marriages",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.thoughts",
)
async def households(ctx: TickContext) -> None:
    laws = await LawBook.load(ctx.session)
    tally = HouseholdTally()
    for household in list(await ctx.session.scalars(select(HouseholdRow).order_by(HouseholdRow.id))):
        await tend_household(ctx, household, laws, tally)
    await tend_aggregates(ctx, tally)
    for key, value in vars(tally).items():
        ctx.count(f"households_{key}", value)


PHASES = (Phase("household_survey", household_survey), Phase("households", households))
