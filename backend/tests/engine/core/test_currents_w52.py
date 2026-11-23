from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.biomes import Biome
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.climes import ClimateOscillationRow, RegionWindRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.climes import CirculationBand, OscillationPhase
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.engine.climes.shifts import clime_shifts, upwelling
from aerona.engine.climes.winds import WindTally, keep_winds
from aerona.engine.context import TickContext
from aerona.engine.cosmos.climate import current_heat
from aerona.engine.environment.dangers import currents
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, tuned_rules

RULES = Rules()


async def at(session: AsyncSession, epoch: int) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "climes", rules=tuned_rules())


async def coasts(session: AsyncSession, world: CoreWorld, tides: int) -> list[RegionEnvironmentRow]:
    await environment_survey(await at(session, 2))
    world.world.tidal_strength = tides
    grounds: list[RegionEnvironmentRow] = []
    for index, region in enumerate(world.regions):
        region.map_x, region.map_y = index * 10.0, 0.0
        ground = await session.get(RegionEnvironmentRow, region.id)
        assert ground is not None
        ground.latitude, ground.coast_kind, ground.biome_mix, ground.current = 10, CoastKind.NONE, [0 for _ in Biome], OceanCurrent.NONE
        grounds.append(ground)
    grounds[0].coast_kind = grounds[-1].coast_kind = CoastKind.BEACH
    await session.flush()
    return grounds


async def test_a_coast_with_wind_off_the_land_wells_up_and_a_narrow_sea_of_strong_tides_runs_tidal(session: AsyncSession, world: CoreWorld) -> None:
    grounds = await coasts(session, world, RULES.currents.tidal_strength_min + 10)
    tally = WindTally()
    await keep_winds(await at(session, 3), tally)
    assert grounds[0].current is OceanCurrent.UPWELLING and tally.upwellings >= 1
    assert grounds[-1].current is OceanCurrent.TIDAL


async def test_weak_tides_leave_a_lee_coast_warm(session: AsyncSession, world: CoreWorld) -> None:
    grounds = await coasts(session, world, RULES.currents.tidal_strength_min - 10)
    await keep_winds(await at(session, 3), WindTally())
    assert grounds[-1].current is OceanCurrent.WARM


async def test_an_upwelling_coast_loses_rain_and_a_warm_phase_cuts_what_it_gives(session: AsyncSession, world: CoreWorld) -> None:
    grounds = await coasts(session, world, 0)
    await keep_winds(await at(session, 3), WindTally())
    coast, inland = world.regions[0].id, world.regions[1].id
    for region in (coast, inland):
        wind = await session.get(RegionWindRow, region)
        assert wind is not None
        wind.band, wind.windward, wind.shadow, wind.monsoon = CirculationBand.DOLDRUMS, False, 0, 0
    await session.flush()
    wet = RULES.winds.doldrums_rain_pct * RULES.winds.band_rain_points // 100
    shifts = await clime_shifts(session, RULES, 3)
    assert grounds[0].current is OceanCurrent.UPWELLING
    assert shifts[inland][0] == wet and shifts[coast][0] == wet - wet * RULES.currents.upwelling_rain_cut_pct // 100
    gain = (RULES.currents.upwelling_catch_pct + RULES.currents.upwelling_fish_pct) / 100
    assert await upwelling(session, RULES, coast) == 1 + gain
    assert await upwelling(session, RULES, inland) == 1.0
    session.add(ClimateOscillationRow(world_id=world.world.id, phase=OscillationPhase.WARM, locked=[]))
    await session.flush()
    assert await upwelling(session, RULES, coast) == 1 + gain * (1 - RULES.currents.warm_phase_upwelling_cut_pct / 100)


def coast_of(current: OceanCurrent) -> RegionEnvironmentRow:
    return RegionEnvironmentRow(river_class=RiverClass.NONE, coast_kind=CoastKind.BEACH, current=current)


def test_currents_warm_or_chill_their_coasts_and_tidal_races_are_dangerous() -> None:
    assert current_heat(RULES, OceanCurrent.WARM) > current_heat(RULES, OceanCurrent.NONE) > current_heat(RULES, OceanCurrent.UPWELLING)
    assert currents(RULES, coast_of(OceanCurrent.TIDAL)) - currents(RULES, coast_of(OceanCurrent.NONE)) == RULES.currents.tidal_danger - max(
        0, RULES.currents.none_danger
    )
    assert currents(RULES, coast_of(OceanCurrent.UPWELLING)) > currents(RULES, coast_of(OceanCurrent.WARM))
