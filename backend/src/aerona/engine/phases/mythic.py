from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mythic.geasa import GeasTally, tend_geasa
from aerona.engine.mythic.heroquests import QuestTally, quest_world
from aerona.engine.mythic.mantling import MantleTally, mantle_world
from aerona.engine.mythic.offices import OfficeTally, tend_offices
from aerona.engine.mythic.servitors import ServitorTally, tend_servitors
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads("table.afflictions", "table.heroquests", "table.reputations")
async def heroquests(ctx: TickContext) -> None:
    tally = QuestTally()
    await quest_world(ctx, tally)
    count(ctx, "heroquest", tally)


@reads("table.reputations")
async def mantling(ctx: TickContext) -> None:
    tally = MantleTally()
    await mantle_world(ctx, tally)
    count(ctx, "mantling", tally)


@reads("table.servitors", "table.spirit_profiles")
async def servitors(ctx: TickContext) -> None:
    tally = ServitorTally()
    await tend_servitors(ctx, tally)
    count(ctx, "servitor", tally)


@reads("table.geasa")
async def geasa(ctx: TickContext) -> None:
    tally = GeasTally()
    await tend_geasa(ctx, tally)
    count(ctx, "geas", tally)


@reads("spirit.unrest", "table.cosmic_offices", "table.routes", "table.spirit_profiles")
@writes("spirit.unrest", "table.cosmic_offices", "table.entities", "table.routes")
async def cosmic_offices(ctx: TickContext) -> None:
    tally = OfficeTally()
    await tend_offices(ctx, tally)
    count(ctx, "office", tally)


PHASES = (
    Phase("heroquests", heroquests),
    Phase("mantling", mantling),
    Phase("servitors", servitors),
    Phase("geasa", geasa),
    Phase("cosmic_offices", cosmic_offices),
)
