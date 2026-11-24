from sqlalchemy.ext.asyncio import AsyncSession

from aerona.engine.demography.cohorts import apply_flow, cohorts_of, seed, total
from aerona.engine.demography.vital import Pressures, demographic_step
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, settlement

CALM = Pressures(fertility=1.0, hunger=0.0, crowding=0.0, disease=0.0, stress=0.0, mortality=1.0)


async def test_the_first_flow_into_a_new_settlement_is_not_counted_twice(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Newfold", world, world.regions[0], population=1447)
    await apply_flow(session, Rules(), town, 1447, category=FlowCategory.MIGRATION, epoch=1)
    assert total(await cohorts_of(session, town.id)) == 1447


async def test_a_swollen_cohort_pool_never_shrinks_the_headcount_it_stands_for(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Newfold", world, world.regions[0], population=1000)
    rows = await seed(session, Rules(), town, 1)
    for row in rows.values():
        row.count *= 2
    await session.flush()
    ctx = await manual_context(session, "pool_probe")
    change = await demographic_step(ctx, town, None, CALM)
    assert total(await cohorts_of(session, town.id)) == 1000 + change
    assert abs(change) < 1000
