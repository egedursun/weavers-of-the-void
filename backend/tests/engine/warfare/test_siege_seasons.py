from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import DefenderAction, SiegeAction, StarvationStage
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.military.logistics import March
from aerona.engine.military.siege import action_for, batter, mend, siege_season, starve, surrenders
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import open_war, raise_army
from aerona.engine.services.war_geography import Neighbourhood
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx, society, tune


async def besiegers(ctx: TickContext, world_id: int) -> tuple[March, WarRow, EntityRow]:
    host = await make(ctx.session, "Iron Folk", EntityType.PEOPLE, world_id, population=20000)
    city = await make(ctx.session, "Highwall", EntityType.SETTLEMENT, world_id, population=2000, defense=40, prosperity=50)
    await society(ctx.session, host.id, warrior=30.0)
    war = await open_war(ctx, host, city)
    war.status = WarStatus.ONGOING
    strength = await MilitaryStrength.load(ctx.session, ctx.rules)
    army, _ = await raise_army(ctx, strength, await SideIndex.load(ctx.session, await Neighbourhood.load(ctx.session, ctx.rules)), host, war)
    profile = await ctx.session.get(ArmyProfileRow, army.id)
    assert profile is not None
    return March(army, host, profile, None, True), war, city


async def test_a_siege_season_eats_the_stores_and_records_what_both_sides_did(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    march, war, city = await besiegers(ctx, world_id)
    session.add(SettlementInfrastructureRow(settlement_entity_id=city.id, walls_level=2, walls_condition=100, gates=2, locked=[]))
    await session.flush()
    first = await siege_season(ctx, war, city, march, garrison=10)
    assert first.siege.rounds == 1 and first.siege.last_action is first.action and first.siege.last_defence is first.defence
    supplies = first.siege.supplies
    second = await siege_season(ctx, war, city, march, garrison=10)
    assert second.siege.id == first.siege.id and second.siege.rounds == 2 and second.siege.supplies < supplies
    assert second.siege.disease_outside > 0


async def test_hunger_turns_to_famine_and_famine_to_surrender(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, tune(Rules(), siegecraft={"surrender_chance": 100}))
    march, war, city = await besiegers(ctx, world_id)
    found = await siege_season(ctx, war, city, march, garrison=10)
    siege = found.siege
    siege.supplies = 0
    await starve(ctx, siege, city, rationing=False)
    assert siege.starvation is StarvationStage.FAMINE
    assert await action_for(ctx, siege, march, 0.0) is SiegeAction.NEGOTIATE
    assert surrenders(ctx, siege, SiegeAction.BLOCKADE)
    siege.locked = ["starvation"]
    siege.starvation = StarvationStage.NONE
    await starve(ctx, siege, city, rationing=True)
    assert siege.starvation is StarvationStage.NONE


async def test_engines_batter_the_walls_and_masons_mend_them(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    march, war, city = await besiegers(ctx, world_id)
    found = await siege_season(ctx, war, city, march, garrison=10)
    siege = found.siege
    walls = SettlementInfrastructureRow(settlement_entity_id=city.id, walls_level=2, walls_condition=100, gates=1, locked=[])
    await batter(ctx, siege, walls, SiegeAction.BOMBARD, 10.0)
    assert walls.walls_condition < 100
    walls.walls_condition = 1
    await batter(ctx, siege, walls, SiegeAction.BLOCKADE, 0.0)
    assert siege.breaches >= 1
    assert await action_for(ctx, siege, march, 1.0) in {SiegeAction.ASSAULT, SiegeAction.BOMBARD}
    walls.walls_condition = 99
    mend(ctx, siege, walls)
    assert walls.walls_condition >= 99
    breaches = siege.breaches
    await batter(ctx, siege, None, SiegeAction.MINE, 0.0)
    assert siege.breaches == breaches + 1


async def test_a_strong_garrison_sallies_out(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    march, war, city = await besiegers(ctx, world_id)
    found = await siege_season(ctx, war, city, march, garrison=10**7)
    assert found.defence is DefenderAction.SALLY and found.siege.sallies == 1
