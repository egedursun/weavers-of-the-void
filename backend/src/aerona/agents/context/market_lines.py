from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.competition import CartelRow, MarketStructureRow, PriceWarRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.competition import EntryBarrier, PriceWarOutcome

TOP_SELLERS = 3


async def structure_line(scope: Scope, row: MarketStructureRow) -> str:
    ranked = sorted(((int(node), share) for node, share in (row.sellers or {}).items()), key=lambda item: (-item[1], item[0]))[:TOP_SELLERS]
    sellers = ", ".join([f"{await named(scope, node)} (seller {node}) {share}" for node, share in ranked])
    small = f", small sellers {row.small_sellers_pct}" if row.small_sellers_pct else ""
    barriers = ", ".join(f"{spoken(EntryBarrier(key))} {value}" for key, value in sorted((row.barriers or {}).items()))
    walls = f"; barriers: {barriers}" if barriers else ""
    return f"the {spoken(row.commodity)} market has {spoken(row.form)}, concentration {row.concentration}: {sellers or 'none named'}{small}{walls}"


async def mortal_market_lines(scope: Scope, me: EntityRow) -> list[str]:
    market = me.location_id
    if market is None:
        return []
    session = scope.session
    found = [
        await structure_line(scope, row)
        for row in await session.scalars(select(MarketStructureRow).where(MarketStructureRow.market_entity_id == market).order_by(MarketStructureRow.id))
    ]
    for cartel in await session.scalars(select(CartelRow).where(CartelRow.broken_epoch.is_(None)).order_by(CartelRow.id)):
        if market in (cartel.markets or []):
            members = ", ".join([await named(scope, node) for node in cartel.members or []])
            found.append(f"compact {cartel.id} of {members} over {spoken(cartel.commodity)} aims at {spoken(cartel.aim)}, discipline {cartel.discipline}")
    for war in await session.scalars(
        select(PriceWarRow).where(PriceWarRow.market_entity_id == market, PriceWarRow.outcome == PriceWarOutcome.ONGOING).order_by(PriceWarRow.id)
    ):
        found.append(f"{await named(scope, war.aggressor_node_id)} sells {spoken(war.commodity)} {war.cut_pct} below its price to drive out its rivals")
    return found
