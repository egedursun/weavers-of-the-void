from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.nature import Dormancy
from aerona.engine.ecology.trophic import appetite, enduring
from aerona.engine.nature.seasons import asleep
from aerona.engine.nature.sleepers import SleeperTally, wake_long_sleepers
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.core.living_kinds import kind, range_of, told

RULES = Rules()


def test_five_dormancies_and_the_new_two_eat_less_or_endure_and_sleep_by_their_bands() -> None:
    assert len(Dormancy) == 5
    assert appetite(RULES, SpeciesProfileRow(dormancy=Dormancy.TORPOR)) == 1 - RULES.dormancy.torpor_food_cut_pct / 100
    assert appetite(RULES, SpeciesProfileRow(dormancy=Dormancy.NONE)) == 1.0
    assert enduring(RULES, SpeciesProfileRow(dormancy=Dormancy.CRYPTOBIOSIS)) < enduring(RULES, SpeciesProfileRow(dormancy=Dormancy.NONE))
    assert asleep(Dormancy.CRYPTOBIOSIS, TemperatureBand.FROZEN) and not asleep(Dormancy.CRYPTOBIOSIS, TemperatureBand.TEMPERATE)


async def test_a_long_sleeper_returns_when_its_land_is_mild_again_and_its_waking_is_told(session: AsyncSession, world: CoreWorld) -> None:
    mild, frozen = world.regions[0], world.regions[1]
    waker = await kind(session, world, "Dust Shrimp", mild, 0, dormancy=Dormancy.CRYPTOBIOSIS)
    sleeper = await kind(session, world, "Ice Shrimp", frozen, 0, dormancy=Dormancy.CRYPTOBIOSIS)
    ctx = await manual_context(session, "dormancy", tuned_rules(dormancy={"cryptobiosis_wake_pct": 100}))
    tally = SleeperTally()
    await wake_long_sleepers(ctx, {mild.id: TemperatureBand.TEMPERATE, frozen.id: TemperatureBand.FROZEN}, tally)
    assert (await range_of(session, waker, mild)).abundance == 100 and tally.woken == 1
    assert (await range_of(session, sleeper, frozen)).abundance == 0
    assert await told(session, "life.woke_from_long_sleep")
