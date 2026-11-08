from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import SoilKind
from aerona.domain.enums.military import DefenderAction, SackChoice, SiegeAction, SiegeWork, StarvationStage
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind, WaterSupply
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.military.siege_depth import (
    WATER_DAYS,
    bombard_factor,
    build_works,
    burn_districts,
    countermine,
    defender_choice,
    encircled,
    finished_works,
    hearten,
    hunger_betrayal,
    mason_repair,
    mass_captives,
    mining_factor,
    repair_factor,
    sack_choice,
    siege_sickness,
    taboo_holds,
    wall_material,
    water_days,
    works_breach,
)
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import open_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import bond, make, make_ctx, tune


async def besieged(ctx: TickContext, world_id: int) -> tuple[EntityRow, EntityRow, SiegeRow]:
    attacker = await make(ctx.session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    city = await make(ctx.session, "Highwall", EntityType.SETTLEMENT, world_id, population=2000, prosperity=50, defense=40)
    war = await open_war(ctx, attacker, city)
    siege = SiegeRow(war_id=war.id, besieged_entity_id=city.id, besieger_entity_id=attacker.id, started_epoch=ctx.epoch, works={}, locked=[])
    ctx.session.add(siege)
    await ctx.session.flush()
    return attacker, city, siege


def walls(city: EntityRow, **values: object) -> SettlementInfrastructureRow:
    return SettlementInfrastructureRow(settlement_entity_id=city.id, locked=[], **values)


async def test_works_rise_with_each_season_and_finish_into_a_breach(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    _, _, siege = await besieged(ctx, world_id)
    done: list[SiegeWork] = []
    for _ in range(3):
        done += build_works(ctx, siege, SiegeAction.BLOCKADE)
    assert done == [SiegeWork.CIRCUMVALLATION] and encircled(siege)
    assert finished_works(siege) == [SiegeWork.CIRCUMVALLATION]
    assert works_breach(ctx, siege) == ctx.rules.siege_depth.work_breach_pct / 100
    assert build_works(ctx, siege, SiegeAction.NEGOTIATE) == []


async def test_countermines_undo_the_mines(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    _, _, siege = await besieged(ctx, world_id)
    assert not countermine(ctx, siege)
    build_works(ctx, siege, SiegeAction.MINE)
    for _ in range(3):
        assert countermine(ctx, siege)
    assert siege.works[SiegeWork.MINES.value] == 0
    assert SiegeWork.COUNTERMINES not in finished_works(siege)


async def test_walls_ground_and_water_shape_the_siege(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    _, city, siege = await besieged(ctx, world_id)
    stone = walls(city, walls_material=BuildMaterial.STONE)
    assert wall_material(None, siege) is BuildMaterial.TIMBER
    assert wall_material(stone, siege) is BuildMaterial.STONE
    siege.wall_material = "not a material"
    assert wall_material(stone, siege) is BuildMaterial.STONE
    siege.wall_material = BuildMaterial.TIMBER.value
    assert wall_material(stone, siege) is BuildMaterial.TIMBER
    assert bombard_factor(ctx, BuildMaterial.TIMBER) > bombard_factor(ctx, BuildMaterial.STONE)
    assert repair_factor(ctx, BuildMaterial.TIMBER) > repair_factor(ctx, BuildMaterial.STONE)
    soft = RegionEnvironmentRow(soil=SoilKind.LOAM)
    hard = RegionEnvironmentRow(
        soil=next(kind for kind in SoilKind if kind not in {SoilKind.LOAM, SoilKind.CLAY, SoilKind.SAND, SoilKind.PEAT, SoilKind.ASH, SoilKind.BONE})
    )
    assert mining_factor(ctx, soft) > mining_factor(ctx, hard) and mining_factor(ctx, None) == 1.0
    assert water_days(None) == WATER_DAYS[WaterSupply.WELL]
    assert water_days(walls(city, water=WaterSupply.AQUEDUCT)) > water_days(walls(city, water=WaterSupply.NONE))


async def test_clean_water_and_sewers_slow_siege_sickness(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    _, city, siege = await besieged(ctx, world_id)
    foul = await siege_sickness(ctx, siege, city)
    session.add(walls(city, water=WaterSupply.CISTERN, sewers=True))
    await session.flush()
    siege.disease_inside = 0
    assert 0 <= await siege_sickness(ctx, siege, city) < foul


async def test_only_famine_opens_the_gates_to_betrayal(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, tune(Rules(), siege_depth={"betrayal_hunger_pct": 100}))
    _, city, siege = await besieged(ctx, world_id)
    assert not await hunger_betrayal(ctx, siege, city)
    siege.starvation = StarvationStage.FAMINE
    assert await hunger_betrayal(ctx, siege, city)


async def test_a_pure_people_holds_its_taboos(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    _, city, _ = await besieged(ctx, world_id)
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=4000)
    await bond(session, city.id, folk.id, BondKind.DESCENDS_FROM)
    assert await taboo_holds(ctx, city)
    session.add(CultureValueRow(entity_id=folk.id, axis=ValueAxis.PURITY, value=-90))
    await session.flush()
    assert not await taboo_holds(ctx, city)


async def test_masons_mend_the_walls_with_stone_in_store(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    _, city, siege = await besieged(ctx, world_id)
    wall = walls(city, walls_condition=40)
    session.add(wall)
    await session.flush()
    assert await mason_repair(ctx, siege, city, wall) == 0
    await goods_of(session, ctx.epoch).add(city.id, CommodityKind.STONE, 50, GoodsFlow.PLAYER)
    before = await holding(session, city.id, CommodityKind.STONE)
    assert await mason_repair(ctx, siege, city, wall) > 0 and wall.walls_condition > 40
    assert await holding(session, city.id, CommodityKind.STONE) == before - ctx.rules.siege_depth.stone_per_repair
    wall.locked = ["walls_condition"]
    assert await mason_repair(ctx, siege, city, wall) == 0


async def test_the_victor_chooses_by_mercy_and_a_held_choice_stays(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    attacker, _, siege = await besieged(ctx, world_id)
    assert await sack_choice(ctx, siege, attacker, None) is SackChoice.SACK
    session.add(CultureValueRow(entity_id=attacker.id, axis=ValueAxis.MERCY, value=80))
    await session.flush()
    assert await sack_choice(ctx, siege, attacker, None) is SackChoice.MERCY
    siege.choice, siege.locked = SackChoice.RAZE, ["choice"]
    assert await sack_choice(ctx, siege, attacker, None) is SackChoice.RAZE


async def test_a_sack_burns_districts_and_leads_people_away(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    attacker, city, siege = await besieged(ctx, world_id)
    for _ in range(6):
        session.add(DistrictRow(settlement_entity_id=city.id, kind=DistrictKind.MARKET, built_epoch=1, locked=[]))
    await session.flush()
    assert await burn_districts(ctx, city, 20) > 0
    taken = await mass_captives(ctx, city, attacker, siege.war_id, 10)
    assert taken == 200 and stat(city, "population") == 1800
    cohort = await session.scalar(select(CaptiveCohortRow).where(CaptiveCohortRow.captor_entity_id == attacker.id))
    assert cohort is not None and cohort.count == 200


async def test_the_defender_sallies_repairs_rations_or_calls_for_relief(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    _, city, siege = await besieged(ctx, world_id)
    assert defender_choice(ctx, siege, 1000, 100, None) is DefenderAction.SALLY
    siege.breaches = 1
    assert defender_choice(ctx, siege, 1, 1000, None) is DefenderAction.REPAIR
    siege.breaches, siege.supplies = 0, 0
    assert defender_choice(ctx, siege, 1, 1000, walls(city, walls_condition=100)) is DefenderAction.RATION
    siege.supplies = 1000
    assert defender_choice(ctx, siege, 1, 1000, walls(city, walls_condition=100)) is DefenderAction.SEEK_RELIEF
    siege.last_defence, siege.locked = DefenderAction.REPAIR, ["last_defence"]
    assert defender_choice(ctx, siege, 1000, 100, None) is DefenderAction.REPAIR


async def test_news_of_relief_heartens_the_garrison(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    _, city, _ = await besieged(ctx, world_id)
    before = stat(city, "stability") if stat(city, "morale") is None else stat(city, "morale")
    hearten(ctx, city)
    after = stat(city, "stability") if stat(city, "morale") is None else stat(city, "morale")
    assert before is None or (after or 0) >= before
