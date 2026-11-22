from sqlalchemy import select

from aerona.db.tables.competition import MarketStructureRow
from aerona.db.write_guard import held
from aerona.engine.competition.cartels import tend_cartels
from aerona.engine.competition.law import break_monopoly
from aerona.engine.competition.structure import survey_markets
from aerona.engine.competition.wars import tend_wars
from aerona.engine.context import TickContext
from aerona.engine.governance.insolvency import InsolvencyTally
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "faction.wealth",
    "people.wealth",
    "table.bonds",
    "table.cartels",
    "table.company_profiles",
    "table.economic_orders",
    "table.faction_profiles",
    "table.holder_techniques",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.market_structures",
    "table.network_nodes",
    "table.network_profiles",
    "table.polity_members",
    "table.price_wars",
    "table.shop_goods",
    "table.shops",
    "table.supply_tiers",
    "table.workshops",
)
@writes("table.market_structures")
async def competition(ctx: TickContext) -> None:
    ctx.count("competition_markets", await survey_markets(ctx))
    structures = [row for row in await ctx.session.scalars(select(MarketStructureRow).order_by(MarketStructureRow.id)) if not held(row.market_entity_id)]
    broken = 0
    for structure in structures:
        broken += 1 if await break_monopoly(ctx, structure) is not None else 0
    cartels = await tend_cartels(ctx, structures)
    tally = InsolvencyTally()
    wars = await tend_wars(ctx, structures, tally)
    ctx.count("competition_monopolies_broken", broken)
    for key, value in cartels.items():
        ctx.count(f"competition_cartels_{key}", value)
    for key, value in wars.items():
        ctx.count(f"competition_wars_{key}", value)
    ctx.count("competition_insolvent", tally.filed)


PHASES = (Phase("competition", competition),)
