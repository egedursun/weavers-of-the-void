from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.war import WarEnding
from aerona.engine.phases.warfare import disband_army, force_battle, raise_war_army
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import declare_war, open_war
from aerona.engine.services.war_resolution import end_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx, tune

QUIET = {"battle_die": 1, "duel_chance": 0, "capture_chance": 0, "four_battle_exhaustion_chance": 0, "decisive_score": 50, "great_victory_diff": 1000}


async def _army_size(session: AsyncSession, owner_id: int) -> int:
    row = await session.scalar(select(ArmyRow).where(ArmyRow.owner_entity_id == owner_id))
    assert row is not None
    entity = await session.get(EntityRow, row.entity_id)
    assert entity is not None
    return stat(entity, "size") or 0


async def test_raising_an_army_takes_soldiers_from_the_population(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, tune(Rules(), campaigns=QUIET))
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=60)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=5000, martiality=40)
    await declare_war(ctx, first.id, second.id, "grudge")
    war = await open_war(ctx, first, second)
    army = await raise_war_army(ctx, war.id, first.id)
    size = stat(army, "size") or 0
    assert size > 0
    assert stat(first, "population") == 9000 - size


async def test_ending_a_war_returns_the_survivors_and_not_the_fallen(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, tune(Rules(), campaigns=QUIET))
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=60)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=5000, martiality=40)
    await declare_war(ctx, first.id, second.id, "grudge")
    war = await open_war(ctx, first, second)
    await force_battle(ctx, war.id)
    before = stat(first, "population") or 0
    survivors = await _army_size(session, first.id)
    await end_war(ctx, war, WarEnding.PEACE, reason="test peace")
    assert stat(first, "population") == before + survivors


async def test_disbanding_by_decree_sends_the_soldiers_home(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, tune(Rules(), campaigns=QUIET))
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=60)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=5000, martiality=40)
    await declare_war(ctx, first.id, second.id, "grudge")
    war = await open_war(ctx, first, second)
    army = await raise_war_army(ctx, war.id, first.id)
    await disband_army(ctx, army.id)
    assert stat(first, "population") == 9000


async def test_an_attacking_walled_city_is_never_the_besieged_side(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, tune(Rules(), campaigns=QUIET))
    city = await make(session, "Stone Gate", EntityType.SETTLEMENT, world_id, population=8000, defense=90, prosperity=50)
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=5000, martiality=40)
    await declare_war(ctx, city.id, folk.id, "grudge")
    war = await open_war(ctx, city, folk)
    await force_battle(ctx, war.id)
    assert await session.scalar(select(SiegeRow).where(SiegeRow.besieged_entity_id == city.id)) is None
