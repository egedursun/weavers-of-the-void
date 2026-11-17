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
    "table.dwelling_kinds",
    "table.dwellings",
    "table.entities",
    "table.household_members",
    "table.households",
    "table.mortal_profiles",
    "table.nodes",
    "table.offices",
    "table.place_profiles",
)
@writes("table.dwelling_kinds", "table.dwellings", "table.household_members", "table.households")
async def household_survey(ctx: TickContext) -> None:
    ctx.count("households_housed", await house_everyone(ctx))


@reads(
    "mortal.age",
    "people.prosperity",
    "settlement.population",
    "settlement.prosperity",
    "table.age_set_members",
    "table.bonds",
    "table.community_cohorts",
    "table.creator_taboos",
    "table.culture_ethics",
    "table.culture_values",
    "table.districts",
    "table.dwelling_furnishings",
    "table.dwelling_kinds",
    "table.dwellings",
    "table.entities",
    "table.geasa",
    "table.house_members",
    "table.house_profiles",
    "table.household_aggregates",
    "table.household_members",
    "table.households",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.marriages",
    "table.memberships",
    "table.mind_facets",
    "table.mind_profiles",
    "table.minds",
    "table.mortal_profiles",
    "table.nodes",
    "table.offices",
    "table.people_culture",
    "table.personality_values",
    "table.place_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.preferences",
    "table.purity",
    "table.region_environment",
    "table.site_profits",
    "table.skills",
    "table.technology_profiles",
    "table.thoughts",
    "table.tradition_profiles",
    "table.union_customs",
    "table.world_maps",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.dwelling_furnishings",
    "table.dwelling_kinds",
    "table.dwellings",
    "table.entities",
    "table.house_profiles",
    "table.household_aggregates",
    "table.household_members",
    "table.households",
    "table.incident_facts",
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
