from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.museums.gardens import GardenTally, keep_gardens
from aerona.engine.museums.hoards import HoardTally, keep_hoards
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "table.bonds",
    "table.entities",
    "table.fossil_beds",
    "table.item_profiles",
    "table.museum_collections",
    "table.museum_pieces",
    "table.offices",
    "table.species_ranges",
    "table.structure_profiles",
)
@writes("table.museum_collections", "table.museum_pieces")
async def collections(ctx: TickContext) -> None:
    tally = HoardTally()
    await keep_hoards(ctx, tally)
    count(ctx, "collections", tally)


@reads(
    "settlement.prosperity",
    "settlement.wealth",
    "table.divine_standing",
    "table.entities",
    "table.game_reserves",
    "table.gardens",
    "table.place_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.species_profiles",
    "table.species_ranges",
    "table.structure_profiles",
)
@writes("table.divine_standing", "table.gardens", "table.polity_profiles")
async def gardens(ctx: TickContext) -> None:
    tally = GardenTally()
    await keep_gardens(ctx, tally)
    count(ctx, "gardens", tally)


PHASES = (Phase("collections", collections), Phase("gardens", gardens))
