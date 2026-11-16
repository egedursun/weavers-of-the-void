from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.mortal import LifeStage
from aerona.engine.law.sentences import reeducate
from aerona.engine.polity.regard import UNKNOWN_DISTANCE, value_distance
from aerona.engine.polity.revolt_causes import contentment
from aerona.engine.powers.phase import grown
from tests.engine.core.factories import CoreWorld, mortal, settlement
from tests.engine.core.test_minds_w44 import at


async def test_only_the_grown_meet_a_power_that_waits_for_its_time(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brightwell", world, world.regions[0])
    child = await mortal(session, "Pell", world, town.id)
    profile = await session.get(MortalProfileRow, child.id)
    ctx = await at(session, 2)
    if profile is None:
        return
    profile.life_stage = LifeStage.CHILD
    assert not await grown(ctx, child)
    profile.life_stage = LifeStage.ADULT
    assert await grown(ctx, child)


async def test_reeducation_moves_the_culprit_s_loyalty_to_the_liege(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Correction", world, world.regions[0])
    culprit = await mortal(session, "Dara", world, town.id)
    profile = await session.get(MortalProfileRow, culprit.id)
    if profile is None:
        return
    before = profile.loyalty_liege
    ctx = await at(session, 2)
    await reeducate(ctx, culprit, None)
    assert profile.loyalty_liege != before or ctx.rules.sentences.reeducation_loyalty == 0


def test_a_town_without_a_society_counts_as_half_content() -> None:
    assert contentment(None) == 50


def test_two_holders_with_no_known_values_are_neither_near_nor_far() -> None:
    assert value_distance({}, {}) == UNKNOWN_DISTANCE
    assert UNKNOWN_DISTANCE > 0
