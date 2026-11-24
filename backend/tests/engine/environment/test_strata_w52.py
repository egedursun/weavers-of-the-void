from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import RegionGeologyRow, RegionStratumRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.geology import RockKind, UndergroundStratum
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.world import WorldType
from aerona.engine.environment.columns import column_depth, stratum_depth
from aerona.engine.environment.deep import deepen, dissolve_salt
from aerona.engine.environment.geology import Layer, lay_columns, strata_for
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, settlement, surveyed, tuned_rules

RULES = Rules()
U = UndergroundStratum
R = RockKind


def physics(*, hydro: int = 60, volcanism: int = 20, tectonics: int = 50) -> WorldPhysicsRow:
    return WorldPhysicsRow(hydrosphere=hydro, volcanism=volcanism, tectonics=tectonics)


def strata(column: list[RockKind], found: WorldPhysicsRow | None, world: WorldType = WorldType.ORDINARY, **kw: bool) -> set[UndergroundStratum]:
    layers = [Layer(rock, 10) for rock in column]
    return {item.stratum for item in strata_for(RULES, layers, found, world, underworld=kw.get("underworld", False), rough=kw.get("rough", False))}


def test_each_stratum_forms_only_where_its_rule_holds() -> None:
    plain = strata([R.SOIL, R.SANDSTONE, R.GRANITE], physics())
    assert U.AQUIFER in plain and U.MAGMA_SEA not in plain and U.RESERVOIR not in plain
    assert U.AQUIFER not in strata([R.SOIL, R.SANDSTONE], physics(hydro=0))
    assert U.RESERVOIR in strata([R.SOIL, R.CLAY, R.COAL, R.GRANITE], physics())
    assert U.RESERVOIR not in strata([R.SOIL, R.COAL, R.CLAY], physics())
    caves = strata([R.SOIL, R.LIMESTONE], physics(tectonics=90), rough=True)
    assert {U.CAVERN_UPPER, U.CAVERN_MIDDLE, U.CAVERN_LOWER} <= caves
    assert U.CAVERN_MIDDLE not in strata([R.SOIL, R.LIMESTONE], physics())
    assert U.MAGMA_SEA in strata([R.BASALT], physics(volcanism=80))
    assert U.UNDER_OCEAN in strata([R.WATER_ICE, R.GRANITE], physics(volcanism=RULES.underground.under_ocean_heat_min))
    assert U.HOLLOW_INTERIOR in strata([R.GRANITE], physics(), WorldType.HOLLOW)
    assert U.DEEP_UNDERWORLD in strata([R.GRANITE], physics(), underworld=True)


def test_an_aquifer_lies_at_the_first_porous_rock_and_caverns_below_the_column() -> None:
    rows = [RegionGeologyRow(rock=rock, thickness=10, veins={}, locked=[]) for rock in (R.SOIL, R.SHALE, R.SANDSTONE, R.GRANITE)]
    assert stratum_depth(RULES, rows, U.AQUIFER) == 10
    assert stratum_depth(RULES, rows, U.CAVERN_UPPER) > column_depth(rows)
    salt = [RegionGeologyRow(rock=R.HALITE, thickness=20, veins={}, locked=[])]
    assert dissolve_salt(50, salt) == 10 and salt[0].thickness == 10


async def test_deep_mining_breaches_the_magma_sea_and_draws_a_reservoir(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    region = world.regions[0]
    town = await settlement(session, "Shaft", world, region)
    ctx = await manual_context(session, "test", tuned_rules(underground={"blowout_pct": 0}))
    for order, rock in enumerate((R.SOIL, R.SHALE, R.GRANITE)):
        session.add(RegionGeologyRow(region_entity_id=region.id, depth_order=order, rock=rock, thickness=5, veins={}, locked=[]))
    magma = RegionStratumRow(region_entity_id=region.id, stratum=U.MAGMA_SEA, volume=0, pressure=0, locked=[])
    reservoir = RegionStratumRow(region_entity_id=region.id, stratum=U.RESERVOIR, volume=40, pressure=60, locked=[])
    session.add_all([magma, reservoir])
    land = await session.get(RegionEnvironmentRow, region.id)
    assert land is not None
    land.mined, land.scars = 100, {}
    await session.flush()
    tally = await deepen(ctx)
    kinds = set(await session.scalars(select(IncidentRow.kind)))
    assert magma.breached_epoch == ctx.epoch and land.scars.get(ScarKind.BURNED.value, 0) >= RULES.underground.magma_breach_scar
    assert {"deep.stratum_reached", "deep.stratum_breached", "deep.reservoir_tapped"} <= kinds
    assert tally.tapped == 1 and reservoir.volume == 40 - RULES.underground.reservoir_draw
    fuel = await session.scalar(select(func.sum(CommunityStockRow.quantity)).where(CommunityStockRow.commodity == CommodityKind.FUEL))
    assert town.id and (fuel or 0) >= RULES.underground.reservoir_draw


async def caves_after_mining(session: AsyncSession, chance: int) -> list[int]:
    world = await seed_core_world(session)
    await surveyed(session, world)
    region = world.regions[0]
    ctx = await manual_context(session, "test", tuned_rules(underground={"cavern_place_pct": chance}))
    for order, rock in enumerate((R.SOIL, R.LIMESTONE)):
        session.add(RegionGeologyRow(region_entity_id=region.id, depth_order=order, rock=rock, thickness=5, veins={}, locked=[]))
    cavern = RegionStratumRow(region_entity_id=region.id, stratum=U.CAVERN_UPPER, volume=0, pressure=0, locked=[])
    session.add(cavern)
    land = await session.get(RegionEnvironmentRow, region.id)
    assert land is not None
    land.mined = 100
    await session.flush()
    await deepen(ctx)
    assert cavern.reached_epoch == ctx.epoch
    atlas = await RegionAtlas.load(session)
    caves = await session.scalars(select(PlaceProfileRow.entity_id).where(PlaceProfileRow.kind == PlaceKind.CAVE))
    return [place for place in caves if atlas.top_region(place) == region.id]


async def test_reaching_a_cavern_can_open_a_cave_in_its_land(session: AsyncSession) -> None:
    assert len(await caves_after_mining(session, 100)) == 1


async def test_a_cavern_opens_no_cave_when_its_chance_is_nil(session: AsyncSession) -> None:
    assert await caves_after_mining(session, 0) == []


async def test_a_hollow_world_keeps_only_its_shafts_to_the_inner_surface(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    world.world.world_type = WorldType.HOLLOW
    await session.flush()
    assert len(world.regions) > 1
    ctx = await manual_context(session, "test", tuned_rules(underground={"hollow_shaft_count": 1}))
    await lay_columns(ctx)
    shafts = await session.scalar(select(func.count()).select_from(RegionStratumRow).where(RegionStratumRow.stratum == U.HOLLOW_INTERIOR))
    assert shafts == 1
