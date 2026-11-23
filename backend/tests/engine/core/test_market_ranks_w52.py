from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.market_ranks import RANKS, by_order, higher_markets
from aerona.db.tables.agrarian import CentralPlaceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.domain.enums.agrarian import CentralityRank
from aerona.domain.enums.gathering import GatheringKind
from aerona.domain.enums.settlement import SizeTier
from aerona.engine.agrarian.rings import SpatialTally, keep_spatial
from aerona.engine.context import TickContext
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules

PLACES = {"weekly_threshold": 1000, "seasonal_threshold": 3000, "rare_threshold": 50000, "metropolitan_threshold": 90000}


async def surveyed(session: AsyncSession, **places: int) -> TickContext:
    ctx = await manual_context(session, "agrarian", rules=tuned_rules(central_places=PLACES | places))
    await environment_survey(ctx)
    return ctx


async def town(session: AsyncSession, world: CoreWorld, name: str, region: int, population: int) -> EntityRow:
    found = await settlement(session, name, world, world.regions[region], population=population)
    session.add(SettlementProfileRow(settlement_entity_id=found.id, size_tier=SizeTier.CITY, treasury=2000, investment_pool=2000, locked=[], foreigners={}))
    session.add(SettlementInfrastructureRow(settlement_entity_id=found.id, roads=0, locked=[]))
    await session.flush()
    return found


async def rank_of(session: AsyncSession, town_id: int) -> CentralityRank | None:
    row = await session.get(CentralPlaceRow, town_id)
    return row.rank if row is not None else None


def test_ranks_climb_in_order_and_only_the_top_is_unique() -> None:
    ordered = by_order()
    assert ordered[0] is CentralityRank.DAILY and ordered[-1] is CentralityRank.METROPOLITAN
    assert [rank for rank, spec in RANKS.items() if spec.unique] == [CentralityRank.METROPOLITAN]
    assert [rank for rank, spec in RANKS.items() if spec.fair] == [CentralityRank.SEASONAL]
    assert higher_markets(CentralityRank.METROPOLITAN) == frozenset()
    assert CentralityRank.METROPOLITAN in higher_markets(CentralityRank.WEEKLY)


async def test_a_seasonal_market_needs_a_fair(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    host = await town(session, world, "Fairholm", 0, 4000)
    await keep_spatial(ctx, SpatialTally())
    assert await rank_of(session, host.id) is CentralityRank.WEEKLY
    session.add(GatheringRow(host_node_id=host.id, kind=GatheringKind.FAIR, epoch=ctx.epoch, locked=[]))
    await session.flush()
    await keep_spatial(ctx, SpatialTally())
    assert await rank_of(session, host.id) is CentralityRank.SEASONAL
    assert "market.rank_changed" in set(await session.scalars(select(IncidentRow.kind)))


async def test_a_world_has_one_metropolitan_market(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, metropolitan_threshold=5000, rare_threshold=4000, metropolitan_range=0, rare_range=0)
    first = await town(session, world, "Highgate", 0, 9000)
    second = await town(session, world, "Lowgate", 3, 8000)
    await keep_spatial(ctx, SpatialTally())
    ranks = [await rank_of(session, first.id), await rank_of(session, second.id)]
    assert ranks.count(CentralityRank.METROPOLITAN) == 1 and ranks[0] is CentralityRank.METROPOLITAN
    assert ranks[1] is CentralityRank.RARE
