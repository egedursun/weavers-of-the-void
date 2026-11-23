from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.biomes import Biome
from aerona.catalog.wind_belts import BELTS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.climes import RegionWindRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.domain.enums.climes import CirculationBand
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.environment import CoastKind
from aerona.engine.climes.shifts import clime_shifts, sea_navigation
from aerona.engine.climes.winds import WindTally, band_of, keep_winds
from aerona.engine.context import TickContext
from aerona.engine.operations.sail import becalmed
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, mortal, settlement, tuned_rules

RULES = Rules()


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "climes", rules=tuned_rules(**rules))


async def laid_out(session: AsyncSession, world: CoreWorld, latitude: int = 10) -> list[RegionEnvironmentRow]:
    await environment_survey(await at(session, 2))
    grounds: list[RegionEnvironmentRow] = []
    for index, region in enumerate(world.regions):
        region.map_x, region.map_y = index * 10.0, 0.0
        ground = await session.get(RegionEnvironmentRow, region.id)
        assert ground is not None
        ground.latitude, ground.coast_kind, ground.biome_mix, ground.current = latitude, CoastKind.NONE, [0 for _ in Biome], OceanCurrent.NONE
        grounds.append(ground)
    await session.flush()
    return grounds


def physics(pressure: float = 1.0, rotation: float = 24.0, locked: bool = False) -> WorldPhysicsRow:
    return WorldPhysicsRow(pressure=pressure, rotation_hours=rotation, tidally_locked=locked)


def test_every_belt_takes_its_place_by_latitude_and_by_the_air_and_day_of_its_world() -> None:
    assert band_of(RULES, None, 0) is CirculationBand.DOLDRUMS
    assert band_of(RULES, None, RULES.winds.subtropical_latitude) is CirculationBand.SUBTROPICAL_CALM
    assert band_of(RULES, None, 20) is CirculationBand.TRADE
    assert band_of(RULES, None, 45) is CirculationBand.WESTERLY
    assert band_of(RULES, None, 75) is CirculationBand.POLAR
    thick = RULES.winds.thick_pressure_tenths / 10 + 1
    assert band_of(RULES, physics(thick, RULES.winds.super_rotation_day_hours + 1), 45) is CirculationBand.SUPER_ROTATION
    assert band_of(RULES, physics(thick, RULES.winds.banded_rotation_hours - 1), 45) is CirculationBand.BANDED
    assert band_of(RULES, physics(1.0, RULES.winds.single_cell_hours + 1), 45) is CirculationBand.SINGLE_CELL
    assert band_of(RULES, physics(0.0), 45) is CirculationBand.STILL
    assert band_of(RULES, physics(locked=True), 45) is CirculationBand.TERMINATOR
    assert {band for band, spec in BELTS.items() if spec.calm} == {CirculationBand.DOLDRUMS, CirculationBand.SUBTROPICAL_CALM, CirculationBand.STILL}


async def test_belts_move_toward_the_summer_half_and_a_shift_is_told(session: AsyncSession, world: CoreWorld) -> None:
    latitude = RULES.winds.subtropical_latitude + RULES.winds.doldrums_width + 2
    await laid_out(session, world, latitude)
    tally = WindTally()
    await keep_winds(await at(session, 3), tally)
    wind = await session.get(RegionWindRow, world.regions[1].id)
    assert wind is not None and wind.band is CirculationBand.WESTERLY and wind.summer_band is CirculationBand.SUBTROPICAL_CALM
    assert tally.read == len(world.regions)
    ground = await session.get(RegionEnvironmentRow, world.regions[1].id)
    assert ground is not None
    ground.latitude = 0
    await session.flush()
    await keep_winds(await at(session, 4), WindTally())
    shifted = await session.get(RegionWindRow, world.regions[1].id)
    assert shifted is not None and shifted.band is CirculationBand.DOLDRUMS
    assert "winds.belt_changed" in set(await session.scalars(select(IncidentRow.kind)))


async def test_each_belt_brings_or_takes_its_rain(session: AsyncSession, world: CoreWorld) -> None:
    await laid_out(session, world)
    wet, dry = world.regions[1].id, world.regions[2].id
    for region, band in ((wet, CirculationBand.DOLDRUMS), (dry, CirculationBand.SUBTROPICAL_CALM)):
        session.add(RegionWindRow(region_entity_id=region, band=band, wind_from=0, strength=10, locked=[]))
    await session.flush()
    shifts = await clime_shifts(session, RULES, 3)
    points = RULES.winds.band_rain_points
    assert shifts[wet][0] == RULES.winds.doldrums_rain_pct * points // 100 > 0
    assert shifts[dry][0] == RULES.winds.subtropical_calm_rain_pct * points // 100 < 0


async def test_calm_belts_slow_ships_and_can_leave_them_becalmed(session: AsyncSession, world: CoreWorld) -> None:
    await laid_out(session, world)
    calm, trade = world.regions[1], world.regions[2]
    session.add(RegionWindRow(region_entity_id=calm.id, band=CirculationBand.DOLDRUMS, wind_from=0, strength=5, locked=[]))
    session.add(RegionWindRow(region_entity_id=trade.id, band=CirculationBand.TRADE, wind_from=2, strength=40, locked=[]))
    first, second = await settlement(session, "Calm Port", world, calm), await settlement(session, "Fair Port", world, trade)
    third = await settlement(session, "Fair Port Two", world, trade)
    await session.flush()
    slow = await sea_navigation(session, RULES, (first.id, first.id), 3)
    quick = await sea_navigation(session, RULES, (second.id, third.id), 3)
    assert slow > quick
    ctx = await at(session, 3)
    ship = await mortal(session, "Helmsman", world, calm.id)
    assert await becalmed(ctx, ship, calm.id, True)
    assert not await becalmed(ctx, ship, calm.id, False)
    assert not await becalmed(ctx, ship, trade.id, True)
    assert "voyage.becalmed" in set(await session.scalars(select(IncidentRow.kind)))
