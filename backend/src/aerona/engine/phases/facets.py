from aerona.engine.context import TickContext
from aerona.engine.facets.practice import FacetTally, keep_facets
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "people.craft",
    "people.piety",
    "people.prosperity",
    "settlement.defense",
    "settlement.piety",
    "settlement.prosperity",
    "settlement.wealth",
    "table.child_standing",
    "table.community_stocks",
    "table.creator",
    "table.crime_cases",
    "table.death_work",
    "table.dimensions",
    "table.entities",
    "table.facet_practices",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.gatherings",
    "table.holder_levels",
    "table.holder_techniques",
    "table.instrument_kinds",
    "table.kin_groups",
    "table.kin_role_duties",
    "table.music_traditions",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.people_culture",
    "table.polity_profiles",
    "table.restraint_customs",
    "table.settlement_profiles",
    "table.sons",
    "table.stars",
    "table.structure_profiles",
    "table.tradition_profiles",
    "table.union_customs",
    "table.worlds",
    "table.youth_standing",
)
@writes(
    "people.craft",
    "people.piety",
    "people.prosperity",
    "settlement.defense",
    "settlement.piety",
    "settlement.prosperity",
    "settlement.wealth",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.facet_practices",
    "table.holder_levels",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.outbreaks",
    "table.settlement_profiles",
)
async def facets(ctx: TickContext) -> None:
    tally = FacetTally()
    await keep_facets(ctx, tally)
    ctx.count("facets_rooted", tally.rooted)
    ctx.count("facets_faded", tally.faded)
    ctx.count("facets_shifted", tally.shifted)
    ctx.count("facets_effects", tally.effects)


PHASES = (Phase("facets", facets),)
