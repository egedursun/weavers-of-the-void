from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.war import WarCause, WarEnding
from aerona.engine.gods.dedication import dedicated_structures, may_anchor
from aerona.engine.gods.incitement import incitement_toll
from aerona.engine.phases.world_age import enter_golden_age, golden_age_effect, golden_age_status, world_age
from aerona.engine.primitives.holds import GOLDEN_AGE_KEY, INCITEMENT_KEY, is_held, set_held
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import open_war
from aerona.engine.services.war_resolution import end_war
from aerona.rules.registry import Rules
from tests.db.factories import make_son
from tests.engine.warfare.factories import bond, make, make_ctx, society, tune


async def test_the_toll_of_an_incited_war_scales_with_battles_and_sides() -> None:
    rules = Rules().incitement
    many = incitement_toll(rules, 100, victor_worships=True, loser_worships=False, has_loser=True)
    assert many.fame == rules.fame_cap
    assert many.existence == rules.patron_victory_existence
    assert many.grieved
    few = incitement_toll(rules, 3, victor_worships=False, loser_worships=True, has_loser=True)
    assert few.fame == 3 * rules.fame_per_battle
    assert few.existence == -rules.patron_defeat_existence
    assert not few.grieved


async def test_ending_an_incited_war_rewards_the_god_and_grieves_the_losers(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    son = await make_son(session, "Strife", world_id)
    victor = await make(session, "Red Folk", EntityType.PEOPLE, world_id, population=4000, martiality=40, prosperity=50)
    loser = await make(session, "Blue Folk", EntityType.PEOPLE, world_id, population=4000, martiality=40, prosperity=50)
    await bond(session, victor.id, son.id, BondKind.WORSHIPS)
    war = await open_war(ctx, victor, loser, cause=WarCause.INCITED, incited_by_son_id=son.id)
    war.battles = 4
    fame, existence = son.fame, son.existence
    await end_war(ctx, war, WarEnding.EXHAUSTION, victor_id=victor.id, loser_id=loser.id)
    rules = ctx.rules.incitement
    assert son.fame == fame + 4 * rules.fame_per_battle
    assert son.existence == existence + rules.patron_victory_existence
    grudge = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == loser.id, MemoryRow.subject_node_id == son.id))
    assert grudge is not None and grudge.kind is MemoryKind.HARMED_ME
    keys = list(await session.scalars(select(ChronicleRow.template_key)))
    assert "war.incitement_reaped" in keys


async def test_a_held_incitement_is_kept_by_the_next_war_between_the_same_sides(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    son = await make_son(session, "Strife", world_id)
    first = await make(session, "Red Folk", EntityType.PEOPLE, world_id, population=4000, martiality=40)
    second = await make(session, "Blue Folk", EntityType.PEOPLE, world_id, population=4000, martiality=40)
    war = await open_war(ctx, first, second, incited_by_son_id=None)
    war.incited_by_son_id = son.id
    await set_held(session, war.event_entity_id, INCITEMENT_KEY, ctx.epoch, True)
    assert await is_held(session, war.event_entity_id, INCITEMENT_KEY, ctx.epoch)
    later = await open_war(ctx, first, second)
    assert later.incited_by_son_id == son.id
    await set_held(session, later.event_entity_id, INCITEMENT_KEY, ctx.epoch, True)
    later.incited_by_son_id = None
    cleared = await open_war(ctx, first, second, incited_by_son_id=son.id)
    assert cleared.incited_by_son_id is None


def test_a_long_golden_age_deepens_then_turns_soft() -> None:
    rules = Rules()
    life = rules.deep_life
    fresh = golden_age_effect(rules, 10, 10)
    assert fresh.prosperity == life.golden_age_prosperity_gain and fresh.decadence == 0
    deep = golden_age_effect(rules, 0, life.golden_age_deepening_epochs * 100)
    assert deep.prosperity == life.golden_age_prosperity_gain + life.golden_age_deepening_steps * life.golden_age_deepening_gain
    assert deep.decadence == life.golden_age_decadence_loss
    never = golden_age_effect(tune(rules, deep_life={"golden_age_decadence_epochs": 0}), 0, 1000)
    assert never.decadence == 0


async def test_a_soft_golden_age_wears_down_warriors_and_the_hold_keeps_it(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, epoch=30)
    folk = await make(session, "Gold Folk", EntityType.PEOPLE, world_id, population=4000, martiality=40, prosperity=10)
    await society(session, folk.id)
    world = await session.get(WorldRow, world_id)
    assert world is not None
    await enter_golden_age(ctx, world, [folk], announce=False)
    row = await session.get(CommunitySocietyRow, folk.id)
    assert row is not None and row.golden_age_since_epoch == 30
    row.golden_age_since_epoch = 30 - ctx.rules.deep_life.golden_age_decadence_epochs
    await enter_golden_age(ctx, world, [folk], announce=False)
    assert stat(folk, "martiality") == 40 - ctx.rules.deep_life.golden_age_decadence_loss
    status = await golden_age_status(session, ctx.rules, world_id, ctx.epoch)
    assert status.active and status.decadence > 0
    await set_held(session, world_id, GOLDEN_AGE_KEY, ctx.epoch, True)
    await world_age(ctx, ctx.epoch + 1)
    assert await has_flag(session, folk.id, EntityFlag.GOLDEN_AGE)
    await set_held(session, world_id, GOLDEN_AGE_KEY, ctx.epoch, False)
    await world_age(ctx, ctx.epoch + 1)
    assert not await has_flag(session, folk.id, EntityFlag.GOLDEN_AGE)


async def test_a_god_may_anchor_to_structures_dedicated_to_them(session: AsyncSession, world_id: int) -> None:
    son = await make_son(session, "Hearth", world_id)
    other = await make_son(session, "Ash", world_id)
    temple = await make(session, "Hearth Temple", EntityType.STRUCTURE, world_id, splendor=40, durability=40, function=40)
    await bond(session, temple.id, son.id, BondKind.WORSHIPS)
    assert [work.id for work in await dedicated_structures(session, son.id)] == [temple.id]
    assert await may_anchor(session, son, temple)
    assert not await may_anchor(session, other, temple)
