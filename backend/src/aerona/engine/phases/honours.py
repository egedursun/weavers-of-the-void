from aerona.engine.context import TickContext
from aerona.engine.honours.veterans import VeteranTally, keep_veterans
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "table.community_cohorts",
    "table.community_relations",
    "table.creator_taboos",
    "table.culture_ethics",
    "table.deed_claims",
    "table.deeds",
    "table.epoch_year_cursors",
    "table.faction_profiles",
    "table.geasa",
    "table.held_identities",
    "table.incident_participants",
    "table.minds",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.settlement_profiles",
    "table.tradition_profiles",
    "table.traits",
    "table.veteran_grants",
    "table.war_sides",
    "table.wars",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.deed_claims",
    "table.deeds",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.polity_members",
    "table.polity_profiles",
    "table.reputations",
    "table.settlement_profiles",
    "table.veteran_grants",
)
async def veterans(ctx: TickContext) -> None:
    tally = VeteranTally()
    await keep_veterans(ctx, tally)
    count(ctx, "veterans", tally)


PHASES = (Phase("veterans", veterans),)
