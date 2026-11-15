from sqlalchemy.ext.asyncio import AsyncSession

from aerona.engine.demography.vital import Pressures, demographic_step
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules


def pressures(time: float) -> Pressures:
    return Pressures(fertility=1.0, hunger=0.8, crowding=0.0, disease=0.0, stress=0.0, mortality=1.0, time=time)


async def test_a_world_where_time_runs_slow_changes_less_in_an_epoch_in_both_births_and_deaths(session: AsyncSession, world: CoreWorld) -> None:
    slow_town = await settlement(session, "Stilltide", world, world.regions[0], population=5000)
    fast_town = await settlement(session, "Quickmere", world, world.regions[1], population=5000)
    await session.flush()
    ctx = await manual_context(session, "time", rules=tuned_rules())
    slow = await demographic_step(ctx, slow_town, None, pressures(0.3))
    fast = await demographic_step(ctx, fast_town, None, pressures(1.0))
    assert fast < slow < 0
