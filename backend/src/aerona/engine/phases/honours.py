from aerona.engine.context import TickContext
from aerona.engine.honours.veterans import VeteranTally, keep_veterans
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "faction.wealth",
    "table.bonds",
    "table.community_cohorts",
    "table.community_relations",
    "table.creator",
    "table.creator_taboos",
    "table.culture_ethics",
    "table.deed_claims",
    "table.deeds",
    "table.dimensions",
    "table.entities",
    "table.faction_profiles",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.geasa",
    "table.held_identities",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.mind_profiles",
    "table.minds",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.professions_of_value",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.settlement_profiles",
    "table.sons",
    "table.speaker_cohorts",
    "table.stars",
    "table.tradition_profiles",
    "table.traits",
    "table.veteran_grants",
    "table.veteran_policies",
    "table.war_sides",
    "table.wars",
    "table.worlds",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.faction_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.name_registry",
    "table.node_births",
    "table.polity_members",
    "table.polity_profiles",
    "table.reputations",
    "table.settlement_profiles",
    "table.veteran_grants",
    "table.veteran_policies",
)
async def veterans(ctx: TickContext) -> None:
    tally = VeteranTally()
    await keep_veterans(ctx, tally)
    count(ctx, "veterans", tally)


PHASES = (Phase("veterans", veterans),)
