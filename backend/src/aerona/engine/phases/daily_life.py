from aerona.engine.context import TickContext
from aerona.engine.daily.life import keep_daily_life
from aerona.engine.daily.seed import seed_daily
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "table.biology_variants",
    "table.bonds",
    "table.care_customs",
    "table.community_relations",
    "table.creator",
    "table.cult_doctrines",
    "table.culture_values",
    "table.dimensions",
    "table.domestic_service",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.household_members",
    "table.households",
    "table.housework",
    "table.leisure_pursuits",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.polity_profiles",
    "table.purifications",
    "table.settlement_profiles",
    "table.sons",
    "table.space_norms",
    "table.stars",
    "table.structure_profiles",
    "table.time_budgets",
    "table.worlds",
)
@writes(
    "table.care_customs",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.cult_doctrines",
    "table.domestic_service",
    "table.entities",
    "table.households",
    "table.housework",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.leisure_pursuits",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.settlement_profiles",
    "table.space_norms",
    "table.time_budgets",
)
async def daily_life(ctx: TickContext) -> None:
    seeded = await seed_daily(ctx)
    ctx.count("daily_seeded_budgets", seeded.budgets)
    ctx.count("daily_seeded_care", seeded.care)
    ctx.count("daily_seeded_space", seeded.space)
    ctx.count("daily_seeded_leisure", seeded.leisure)
    ctx.count("daily_seeded_houses", seeded.houses)
    tally = await keep_daily_life(ctx)
    ctx.count("daily_stressed", tally.stressed)
    ctx.count("daily_gladdened", tally.gladdened)
    ctx.count("daily_towns_kept", tally.towns_kept)
    ctx.count("daily_shamed", tally.shamed)
    ctx.count("daily_households", tally.households)
    ctx.count("daily_duties_breached", tally.breached_duties)
    ctx.count("daily_servants_left", tally.servants_left)
    ctx.count("daily_tours", tally.tours)
    ctx.count("daily_breaches", tally.breaches)
    ctx.count("daily_trends", tally.trends)


PHASES = (Phase("daily_life", daily_life),)
