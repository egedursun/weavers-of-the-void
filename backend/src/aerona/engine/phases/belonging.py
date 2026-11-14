from aerona.engine.belonging.identities import IdentityTally, keep_identities
from aerona.engine.belonging.peers import PeerTally, keep_peers
from aerona.engine.belonging.sanctuary import SanctuaryTally, keep_sanctuaries
from aerona.engine.belonging.satire import SatireTally, keep_satire
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "table.army_profiles",
    "table.coalition_members",
    "table.districts",
    "table.held_identities",
    "table.house_members",
    "table.marriages",
    "table.movements",
    "table.nodes",
    "table.notable_years",
    "table.peer_groups",
    "table.polity_members",
    "table.polity_profiles",
    "table.purity_ranks",
)
@writes("table.held_identities")
async def belonging(ctx: TickContext) -> None:
    identities, peers = IdentityTally(), PeerTally()
    await keep_identities(ctx, identities)
    await keep_peers(ctx, peers)
    count(ctx, "identities", identities)
    count(ctx, "peers", peers)


@reads("table.crime_cases", "table.defections", "table.outlaws", "table.sanctuaries", "table.social_norms")
async def sanctuary(ctx: TickContext) -> None:
    tally = SanctuaryTally()
    await keep_sanctuaries(ctx, tally)
    count(ctx, "sanctuary", tally)


@reads("table.offices", "table.satires")
async def satire(ctx: TickContext) -> None:
    tally = SatireTally()
    await keep_satire(ctx, tally)
    count(ctx, "satire", tally)


PHASES = (
    Phase("belonging", belonging),
    Phase("sanctuary", sanctuary),
    Phase("satire", satire),
)
