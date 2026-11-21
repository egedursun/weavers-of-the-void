import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mortal import MortalProfileRow
from aerona.engine.context import TickContext
from aerona.engine.mortal.standing import shift_standing, standing_of
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
