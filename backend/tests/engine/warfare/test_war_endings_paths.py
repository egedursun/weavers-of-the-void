from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.warfare import ArmyRow, WarRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.war import SiegeStatus, WarStatus
from aerona.engine.military.naval import SeaFight
from aerona.engine.military.siege import siege_season
from aerona.engine.phases.warfare import _sea_report, _surrender, _weary_peace
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import OngoingWar, open_war, raise_army
from aerona.engine.services.war_geography import Neighbourhood
from tests.engine.warfare.factories import make, make_ctx
from tests.engine.warfare.test_siege_seasons import besiegers


async def keys(session: AsyncSession) -> set[str]:
    return set(await session.scalars(select(ChronicleRow.template_key)))


async def test_a_worn_out_side_sues_for_peace_or_concedes_when_behind(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    war = await open_war(ctx, first, second)
    war.status = WarStatus.ONGOING
    await _weary_peace(ctx, OngoingWar(war, first.id, second.id), first.id, behind=False)
    assert war.status is WarStatus.ENDED and "war.weary_peace" in await keys(session)
    third = await make(session, "Ash Folk", EntityType.PEOPLE, world_id, population=4000)
    other = await open_war(ctx, first, third)
    other.status = WarStatus.ONGOING
    await _weary_peace(ctx, OngoingWar(other, first.id, third.id), third.id, behind=True)
    assert other.status is WarStatus.ENDED


async def test_a_starved_city_opens_its_gates_and_is_sacked(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    march, war, city = await besiegers(ctx, world_id)
    step = await siege_season(ctx, war, city, march, garrison=10)
    army_row = await session.get(ArmyRow, march.army.id)
    assert army_row is not None
    strength = await MilitaryStrength.load(session, ctx.rules)
    guard, guard_row = await raise_army(ctx, strength, await SideIndex.load(session, await Neighbourhood.load(session, ctx.rules)), city, war)
    armies = {march.owner.id: (march.army, army_row), city.id: (guard, guard_row)}
    await _surrender(ctx, OngoingWar(war, march.owner.id, city.id), (march.owner, city), step, marches=[march], armies=armies)
    assert step.siege.status is SiegeStatus.SURRENDERED and "war.siege.surrender" in await keys(session)
    assert (await session.get(WarRow, war.id)) is not None


async def test_a_sea_battle_is_reported(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    march, _, _ = await besiegers(ctx, world_id)
    await _sea_report(ctx, SeaFight(march, march, {march.army.id: 2}))
    assert "war.sea_battle" in await keys(session)
