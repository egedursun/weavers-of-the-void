from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.leagues.tend import tend_leagues
from aerona.engine.phase import Phase


@reads(
    "table.entities",
    "table.league_decisions",
    "table.league_members",
    "table.nodes",
    "table.polity_leagues",
    "table.polity_members",
    "table.treaty_parties",
    "table.treaty_profiles",
)
@writes("table.applied_fixups", "table.community_societies", "table.league_decisions", "table.league_members", "table.polity_leagues", "table.trade_policies")
async def leagues(ctx: TickContext) -> None:
    for key, value in asdict(await tend_leagues(ctx)).items():
        ctx.count(f"leagues_{key}", value)


PHASES = (Phase("leagues", leagues),)
