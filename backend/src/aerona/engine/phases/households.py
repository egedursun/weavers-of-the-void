from sqlalchemy import select

from aerona.db.tables.households import HouseholdRow
from aerona.engine.context import TickContext
from aerona.engine.households.formation import house_everyone
from aerona.engine.households.homes import backfill_dwellings
from aerona.engine.households.life import HouseholdTally, tend_aggregates, tend_household
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.polity.laws import LawBook


@reads(
    "settlement.population",
    "table.bonds",
    "table.deep_passages",
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
    "item.damage",
    "item.protection",
    "mortal.age",
    "people.prosperity",
    "settlement.population",
    "settlement.prosperity",
    "table.age_set_members",
    "table.bias_weights",
    "table.bonds",
    "table.child_standing",
    "table.community_cohorts",
    "table.creator",
    "table.creator_taboos",
    "table.culture_ethics",
    "table.culture_values",
    "table.deed_claims",
    "table.deeds",
    "table.dimensions",
    "table.districts",
    "table.dwelling_furnishings",
    "table.dwelling_kinds",
    "table.dwellings",
    "table.entities",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.foreign_gods",
    "table.furnishing_kinds",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.geasa",
    "table.house_members",
    "table.house_profiles",
    "table.household_aggregates",
    "table.household_members",
    "table.households",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.kin_group_members",
    "table.kin_groups",
    "table.kind_holdings",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.marriages",
    "table.memberships",
    "table.mind_facets",
    "table.mind_profiles",
    "table.minds",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.people_culture",
    "table.personality_values",
    "table.place_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.preferences",
    "table.professions_of_value",
    "table.purity",
    "table.region_environment",
    "table.reputations",
    "table.site_profits",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.technology_profiles",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.union_customs",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.deed_claims",
    "table.deeds",
    "table.dwelling_furnishings",
    "table.dwelling_kinds",
    "table.dwellings",
    "table.entities",
    "table.faction_memberships",
    "table.house_profiles",
    "table.household_aggregates",
    "table.household_members",
    "table.households",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.marriages",
    "table.memories",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.professions_of_value",
    "table.reputations",
    "table.thoughts",
)
async def households(ctx: TickContext) -> None:
    ctx.count("dwellings_rederived", await backfill_dwellings(ctx))
    laws = await LawBook.load(ctx.session)
    tally = HouseholdTally()
    for household in list(await ctx.session.scalars(select(HouseholdRow).order_by(HouseholdRow.id))):
        await tend_household(ctx, household, laws, tally)
    await tend_aggregates(ctx, tally)
    for key, value in vars(tally).items():
        ctx.count(f"households_{key}", value)


PHASES = (Phase("household_survey", household_survey), Phase("households", households))
