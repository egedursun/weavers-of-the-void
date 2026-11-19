from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.works.building import keep_works
from aerona.engine.works.enterprise import keep_enterprises
from aerona.engine.works.seed import seed_works


@reads(
    "table.currencies",
    "table.entities",
    "table.faction_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.public_works",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.shop_goods",
    "table.shops",
    "table.state_enterprises",
    "table.trade_route_profiles",
)
@writes(
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.currencies",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.public_works",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.shops",
    "table.state_enterprises",
    "table.trade_route_profiles",
)
async def public_works(ctx: TickContext) -> None:
    ctx.count("works_seeded", await seed_works(ctx))
    works = await keep_works(ctx)
    ctx.count("works_stages", works.stages)
    ctx.count("works_delayed", works.delayed)
    ctx.count("works_finished", works.finished)
    ctx.count("works_failed", works.failed)
    ctx.count("works_neglected", works.neglected)
    enterprises = await keep_enterprises(ctx)
    ctx.count("enterprise_revenue", enterprises.revenue)
    ctx.count("enterprise_skimmed", enterprises.skimmed)
    ctx.count("enterprise_starved", enterprises.starved)
    ctx.count("enterprise_privatised", enterprises.privatised)


PHASES = (Phase("public_works", public_works),)
