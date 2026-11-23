from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.rocks import ROCKS
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import RegionGeologyRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.environment import CoastKind, SoilKind, TerrainKind
from aerona.domain.enums.geology import BuildingGrade, RockKind
from aerona.domain.enums.world import WorldType
from aerona.engine.environment.columns import carvable, quarry_grade, rock_cut
from aerona.engine.environment.deep import deepen
from aerona.engine.environment.geology import column_for, lay_columns, sediments, veins_for
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, surveyed, tuned_rules

RULES = Rules()


def ground(
    terrain: TerrainKind, *, soil: SoilKind = SoilKind.LOAM, forest: int = 0, wetland: int = 0, coast: CoastKind = CoastKind.NONE
) -> RegionEnvironmentRow:
    return RegionEnvironmentRow(dominant_terrain=terrain, soil=soil, base_forest=forest, base_wetland=wetland, coast_kind=coast, mineral_layers={}, locked=[])


def layer(rock: RockKind, order: int, *, reached: bool = False) -> RegionGeologyRow:
    return RegionGeologyRow(region_entity_id=1, depth_order=order, rock=rock, thickness=10, veins={}, reached_epoch=1 if reached else None, locked=[])


def test_a_column_follows_its_land_from_soil_down_to_bedrock() -> None:
    rocks = [item.rock for item in column_for(ground(TerrainKind.DESERT), None, WorldType.ORDINARY, SeededRandom(RandomKey(1, 0, "rock")))]
    assert rocks[0] is RockKind.SOIL and RockKind.HALITE in rocks and RockKind.SAND in rocks and rocks[-1] is RockKind.GRANITE
    wooded = [item.rock for item in sediments(ground(TerrainKind.FOREST, forest=80))]
    assert RockKind.COAL in wooded and RockKind.COAL not in [item.rock for item in sediments(ground(TerrainKind.PLAIN))]
    assert [item.rock for item in sediments(ground(TerrainKind.KARST))][-1] is RockKind.LIMESTONE
    assert RockKind.CHALK in [item.rock for item in sediments(ground(TerrainKind.PLAIN, coast=CoastKind.BEACH))]
    crystal = column_for(ground(TerrainKind.PLAIN), None, WorldType.CRYSTAL, SeededRandom(RandomKey(1, 0, "rock")))
    assert crystal[-1].rock is RockKind.CRYSTAL_BEDROCK


def test_a_vein_lies_in_the_first_rock_that_carries_it() -> None:
    column = column_for(ground(TerrainKind.PLAIN), None, WorldType.ORDINARY, SeededRandom(RandomKey(2, 0, "rock")))
    veins = veins_for(RULES, column, {"tin": 0, "lead": 55})
    tin = next(index for index, found in enumerate(veins) if "tin" in found)
    lead = next(index for index, found in enumerate(veins) if "lead" in found)
    assert column[tin].rock is RockKind.GRANITE and veins[tin]["tin"] == RULES.rocks.vein_richness
    assert column[lead].rock is RockKind.LIMESTONE and veins[lead]["lead"] == 55


def test_hard_rock_slows_mining_until_better_tools_cut_it() -> None:
    granite = [layer(RockKind.SOIL, 0, reached=True), layer(RockKind.GRANITE, 1, reached=True)]
    bare = rock_cut(RULES, granite, set())
    tooled = rock_cut(RULES, granite, {Technique.IRON, Technique.BRONZE})
    assert bare > tooled >= 0
    assert rock_cut(RULES, [layer(RockKind.GRANITE, 0)], set()) == 0.0
    assert rock_cut(RULES, [layer(RockKind.CHALK, 0, reached=True)], set()) < bare


def test_stone_grade_and_carving_read_the_rock_beneath() -> None:
    assert quarry_grade([layer(RockKind.SOIL, 0, reached=True), layer(RockKind.MARBLE, 1, reached=True)]) is BuildingGrade.SPLENDID
    assert quarry_grade([layer(RockKind.SOIL, 0), layer(RockKind.SHALE, 1)]) is BuildingGrade.PLAIN
    soft = ROCKS[RockKind.TUFF].workability(RULES) >= RULES.rocks.carve_workability
    assert carvable(RULES, [layer(RockKind.SOIL, 0), layer(RockKind.TUFF, 1)]) is soft
    assert not carvable(RULES, [layer(RockKind.SOIL, 0), layer(RockKind.GRANITE, 1)])


async def test_columns_are_laid_once_and_mining_reaches_layers_veins_and_coal(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    rules = tuned_rules(rocks={"coal_gas_pct": 100})
    ctx = await manual_context(session, "test", rules)
    laid = await lay_columns(ctx)
    assert laid > 0 and await lay_columns(ctx) == 0
    region = world.regions[0].id
    land = await session.get(RegionEnvironmentRow, region)
    assert land is not None
    rows = list(await session.scalars(select(RegionGeologyRow).where(RegionGeologyRow.region_entity_id == region).order_by(RegionGeologyRow.depth_order)))
    assert rows and rows[0].rock is RockKind.SOIL
    rows[1].rock = RockKind.COAL
    rows[1].veins = {"sulfur": 30}
    land.mined = 100
    land.mineral_layers = {}
    await session.flush()
    tally = await deepen(ctx)
    kinds = set(await session.scalars(select(IncidentRow.kind)))
    assert tally.layers > 0 and tally.veins > 0 and "geology.layer_reached" in kinds and "geology.vein_found" in kinds
    assert land.mineral_layers.get("sulfur") == 30
    assert tally.fires == 1 and "mine.gas_fire" in kinds
