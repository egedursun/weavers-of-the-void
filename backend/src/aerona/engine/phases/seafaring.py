from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.military.vessels import seas
from aerona.engine.phase import Phase


@reads(
    "outer_being.interest",
    "table.applied_fixups",
    "table.army_officers",
    "table.bonds",
    "table.calendars",
    "table.claims",
    "table.community_cohorts",
    "table.community_stocks",
    "table.currencies",
    "table.districts",
    "table.entities",
    "table.feuds",
    "table.forced_weather",
    "table.goods",
    "table.holder_levels",
    "table.house_members",
    "table.house_profiles",
    "table.injuries",
    "table.law_profiles",
    "table.learned_tactics",
    "table.loans",
    "table.memories",
    "table.mercenary_contracts",
    "table.nodes",
    "table.offices",
    "table.peace_terms",
    "table.place_environment",
    "table.polity_members",
    "table.polity_profiles",
    "table.region_environment",
    "table.routes",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.skills",
    "table.sky_events",
    "table.spy_agents",
    "table.stars",
    "table.treaty_clauses",
    "table.treaty_profiles",
    "table.unit_designs",
    "table.vessel_profiles",
    "table.workshops",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "outer_being.interest",
    "people.wealth",
    "settlement.wealth",
    "table.applied_fixups",
    "table.army_officers",
    "table.battle_casualties",
    "table.battle_stacks",
    "table.bonds",
    "table.captive_cohorts",
    "table.captives",
    "table.chronicle",
    "table.claims",
    "table.community_cohorts",
    "table.community_stocks",
    "table.currencies",
    "table.districts",
    "table.entities",
    "table.feuds",
    "table.goods",
    "table.house_members",
    "table.house_profiles",
    "table.learned_tactics",
    "table.loans",
    "table.maimed_cohorts",
    "table.memories",
    "table.mercenary_contracts",
    "table.offices",
    "table.peace_terms",
    "table.polity_profiles",
    "table.region_environment",
    "table.routes",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.spy_agents",
    "table.spy_networks",
    "table.treaty_breaches",
    "table.vessel_profiles",
)
async def seafaring(ctx: TickContext) -> None:
    tally = await seas(ctx)
    for key, value in vars(tally).items():
        if isinstance(value, int):
            ctx.count(f"sea_{key}", value)
    for key, value in vars(tally.sail).items():
        ctx.count(f"sail_{key}", value)


PHASES = (Phase("seafaring", seafaring),)
