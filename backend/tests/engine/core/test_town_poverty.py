from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.settlement import SizeTier
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import collect_taxes, keep_order
from tests.engine.core.factories import CoreWorld, settlement


async def test_a_town_s_poverty_and_taxes_follow_its_people_s_prosperity_not_its_emptied_purse(session: AsyncSession, world: CoreWorld) -> None:
    town_row = await settlement(session, "Emptypurse", world, world.regions[0], prosperity=70)
    session.add(SettlementProfileRow(settlement_entity_id=town_row.id, size_tier=SizeTier.TOWN, public_order=50, crime=0, tax_rate=20, locked=[]))
    await session.flush()
    ctx = await manual_context(session, "poverty")
    found: list[tuple[int, int, int]] = []
    for purse in (0, 100):
        set_stats(town_row, wealth=purse)
        town = await town_of(ctx, town_row, await KnowledgeMap.load(session))
        town.profile.public_order, town.profile.crime, town.profile.treasury = 50, 0, 0
        await keep_order(ctx, town, justice=0.5, bands=[], hierarchy=0)
        found.append((town.profile.crime, town.profile.public_order, await collect_taxes(ctx, town)))
    assert found[0] == found[1]
    crime, order, taxes = found[0]
    assert crime < 40 and order > 0 and taxes > 0
