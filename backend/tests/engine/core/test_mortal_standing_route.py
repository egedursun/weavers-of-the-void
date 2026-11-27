import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.context import TickContext
from aerona.engine.mortal.standing import add_honour, add_renown, add_wealth, shift_standing, standing_of
from aerona.engine.primitives.stats import MisroutedStanding, set_stats, shift_stat
from tests.engine.core.factories import CoreWorld, mortal, settlement


async def test_a_mortals_standing_is_moved_in_its_profile_and_a_stat_write_of_it_is_refused(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Standwick", world, world.regions[0])
    hero = await mortal(session, "Aster Moll", world, town.id)
    with pytest.warns(MisroutedStanding):
        shift_stat(hero, "renown", 5, 0)
    with pytest.warns(MisroutedStanding):
        set_stats(hero, wealth=10)
    await shift_standing(session, hero, "renown", 12, ctx.epoch)
    await shift_standing(session, hero, "piety", 7, ctx.epoch)
    profile = await session.get(MortalProfileRow, hero.id)
    assert profile is not None and profile.renown == 12 and await standing_of(session, hero, "renown") == 12
    assert await standing_of(session, hero, "piety") == profile.loyalty_god
    before = await standing_of(session, town, "prosperity")
    await shift_standing(session, town, "prosperity", 5, ctx.epoch, default=0)
    assert await standing_of(session, town, "prosperity") == (before or 0) + 5


async def test_the_standing_of_the_dead_stays_where_death_left_it_while_their_fame_may_grow(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Stillmoor", world, world.regions[0])
    gone = await mortal(session, "Vovka", world, town.id)
    row = await add_honour(session, gone.id, 10, 1)
    before = (row.honour, row.wealth)
    gone.status, gone.end_epoch = EntityStatus.DEAD, 1
    await session.flush()
    await add_honour(session, gone.id, 20, 2)
    await add_wealth(session, gone.id, 20, 2)
    renowned = await add_renown(session, gone.id, 20, 2)
    assert (renowned.honour, renowned.wealth) == before and renowned.renown >= 20
