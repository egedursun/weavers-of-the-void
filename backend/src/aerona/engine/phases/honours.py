from aerona.engine.context import TickContext
from aerona.engine.honours.veterans import VeteranTally, keep_veterans
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads("table.community_cohorts", "table.faction_profiles", "table.polity_members", "table.veteran_grants", "table.war_sides", "table.wars")
@writes("table.polity_members", "table.veteran_grants")
async def veterans(ctx: TickContext) -> None:
    tally = VeteranTally()
    await keep_veterans(ctx, tally)
    count(ctx, "veterans", tally)


PHASES = (Phase("veterans", veterans),)
