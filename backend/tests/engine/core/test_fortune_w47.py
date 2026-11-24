from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.folkways import MishapRow
from aerona.db.tables.fortune import CohortMishapRateRow, FortuneLawRow, FortuneProfileRow, FortuneSourceRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.folkways import MishapKind
from aerona.domain.enums.fortune import FortuneLaw, FortuneSourceKind
from aerona.domain.enums.settlement import SizeTier
from aerona.engine.fortune.cohorts import keep_cohort_mishaps
from aerona.engine.fortune.everyday import everyday, trigger
from aerona.engine.fortune.profiles import keep_fortune, shift_fortune, streak_of
from tests.engine.core.factories import CoreWorld, mortal, settlement
from tests.engine.core.test_minds_w44 import at


async def test_a_streak_stays_within_its_bounds_and_drifts(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 20)
    streaks = {streak_of(ctx, node) for node in range(1, 60)}
    assert all(abs(value) <= ctx.rules.fortune.streak_cap for value in streaks)
    assert len(streaks) > 1


async def test_fortune_is_the_sum_of_its_sources_and_the_divine_law_keeps_only_the_gods(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    being = await mortal(session, "Ila Venn", world, town.id)
    ctx = await at(session, 2, fortune={"streak_step": 0})
    await shift_fortune(ctx, being.id, 20, FortuneSourceKind.CHARM)
    await shift_fortune(ctx, being.id, -5, FortuneSourceKind.DIVINE_DISFAVOUR)
    await keep_fortune(ctx)
    profile = await session.get(FortuneProfileRow, being.id)
    assert profile is not None and profile.fortune == 15
    session.add(FortuneLawRow(world_id=world.world.id, law=FortuneLaw.DIVINE, locked=[]))
    await session.flush()
    await keep_fortune(ctx)
    assert profile.fortune == -5


async def test_a_held_fortune_is_not_reckoned_anew(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    being = await mortal(session, "Ila Venn", world, town.id)
    session.add(FortuneProfileRow(node_id=being.id, fortune=70, streak=0, updated_epoch=1, locked=["fortune"]))
    await session.flush()
    ctx = await at(session, 2)
    await shift_fortune(ctx, being.id, -40, FortuneSourceKind.CURSE)
    await keep_fortune(ctx)
    profile = await session.get(FortuneProfileRow, being.id)
    assert profile is not None and profile.fortune == 70


async def test_everyday_mishaps_befall_the_folk_of_a_town(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    folk = [(await mortal(session, f"Folk {index}", world, town.id)).id for index in range(6)]
    ctx = await at(session, 2, everyday_mishaps={"small_per_epoch": 100})
    befallen = await everyday(ctx, folk)
    assert len(befallen) == len(folk)
    assert all(found.severity >= 1 for found in befallen)


async def test_a_triggered_deadly_mishap_wounds_by_its_kind(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    being = await mortal(session, "Ila Venn", world, town.id)
    happened = await trigger(await at(session, 2), being, MishapKind.FALL, 3)
    assert happened.severity >= 3


async def test_towns_count_their_accidental_dead_each_epoch(session: AsyncSession, world: CoreWorld) -> None:
    ordinary = await settlement(session, "Greenmere", world, world.regions[0], population=10000)
    crowded = await settlement(session, "Stackwell", world, world.regions[0], population=10000)
    session.add(SettlementProfileRow(settlement_entity_id=crowded.id, size_tier=SizeTier.TOWN, fire_risk=80, locked=[], foreigners={}))
    await session.flush()
    ctx = await at(session, 2)
    assert await keep_cohort_mishaps(ctx) >= 2
    assert await keep_cohort_mishaps(ctx) == 0
    calm = await session.get(CohortMishapRateRow, (ordinary.id, 2))
    pressed = await session.get(CohortMishapRateRow, (crowded.id, 2))
    assert calm is not None and calm.dead == 0
    assert pressed is not None and pressed.dead > 0
    assert await session.scalar(select(func.count()).select_from(MishapRow)) == 0
    assert await session.scalar(select(func.count()).select_from(FortuneSourceRow)) == 0
