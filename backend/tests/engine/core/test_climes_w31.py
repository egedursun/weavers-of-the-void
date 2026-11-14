from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.biomes import Biome
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.climes import ClimateOscillationRow, CosmopolitanCultureRow, CosmopolitanMemberRow, LaunchWindowRow, MonsoonSeasonRow, RegionWindRow
from aerona.db.tables.culture import SpeakerCohortRow
from aerona.db.tables.environment import NotableYearRow, RegionEnvironmentRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.climes import CirculationBand, OscillationPhase
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.culture import RumourChannel, SpeakerKind
from aerona.domain.enums.environment import CoastKind, NotableYearKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus, TravelMethod
from aerona.engine.climes.crossings import CrossingTally, keep_cultures, keep_windows
from aerona.engine.climes.seasons import SeasonTally, keep_seasons
from aerona.engine.climes.shifts import clime_shifts, current_coasts, fire_wind, sea_navigation
from aerona.engine.climes.windows import window_delay
from aerona.engine.climes.winds import WindTally, keep_winds
from aerona.engine.context import TickContext
from aerona.engine.lore.rumours import links
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, add_empty_world, bond, mortal, settlement, tuned_rules

MOUNTAIN_MIX = [100 if biome is Biome.MOUNTAINS else 0 for biome in Biome]


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "climes", rules=tuned_rules(**rules))


async def laid_out(session: AsyncSession, world: CoreWorld) -> dict[int, RegionEnvironmentRow]:
    await environment_survey(await at(session, 2))
    grounds: dict[int, RegionEnvironmentRow] = {}
    for index, region in enumerate(world.regions):
        region.map_x, region.map_y = index * 10.0, 0.0
        ground = await session.get(RegionEnvironmentRow, region.id)
        assert ground is not None
        ground.latitude, ground.coast_kind, ground.biome_mix, ground.current = 10, CoastKind.NONE, [0 for _ in Biome], OceanCurrent.NONE
        grounds[index] = ground
    grounds[0].coast_kind = CoastKind.BEACH
    grounds[2].biome_mix = MOUNTAIN_MIX
    await session.flush()
    return grounds


async def test_trade_winds_cast_a_rain_shadow_raise_cold_water_and_carry_foul_air_downwind(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    grounds = await laid_out(session, world)
    first, lee, peak, far = (region.id for region in world.regions)
    grounds[3].coast_kind = CoastKind.BEACH
    session.add(RegionPollutionRow(region_node_id=peak, air=50, water=0, soil=0, polluters={}, epoch=2, locked=[]))
    await session.flush()
    tally = WindTally()
    await keep_winds(await at(session, 3), tally)
    shadowed = await session.get(RegionWindRow, lee)
    assert shadowed is not None and shadowed.band is CirculationBand.TRADE and shadowed.wind_from == 2 and shadowed.shadow == rules.winds.shadow
    mountain = await session.get(RegionWindRow, peak)
    assert mountain is not None and mountain.windward and mountain.shadow == 0
    coast = await session.get(RegionWindRow, first)
    assert coast is not None and coast.upwelling and coast.monsoon == rules.monsoons.strength and grounds[0].current is OceanCurrent.COLD
    far_coast = await session.get(RegionWindRow, far)
    assert far_coast is not None and not far_coast.upwelling and grounds[3].current is OceanCurrent.WARM
    downwind = await session.get(RegionPollutionRow, lee)
    assert downwind is not None and downwind.air > 0 and tally.drifted >= 1 and tally.shadows >= 1
    shifts = await clime_shifts(session, rules, 3)
    assert shifts[lee][0] == -rules.winds.shadow
    assert shifts[peak][0] == rules.winds.windward_rain
    assert await fire_wind(session, rules, lee) == 1 + rules.winds.trade_strength / 100 * rules.winds.fire_wind_pct / 100


async def test_a_held_wind_keeps_the_direction_a_god_gave_it(session: AsyncSession, world: CoreWorld) -> None:
    await laid_out(session, world)
    lee = world.regions[1].id
    session.add(RegionWindRow(region_entity_id=lee, band=CirculationBand.TRADE, wind_from=5, strength=40, locked=["wind_from"]))
    await session.flush()
    await keep_winds(await at(session, 3), WindTally())
    wind = await session.get(RegionWindRow, lee)
    assert wind is not None and wind.wind_from == 5 and wind.read_epoch == 3


async def test_a_failed_monsoon_is_a_hungry_year_and_endangers_the_sea_roads_of_its_coast(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(monsoons={"swing": 0, "fail_below": 150})
    await laid_out(session, world)
    port = await settlement(session, "Brinehold", world, world.regions[0], prosperity=50)
    inland = await settlement(session, "Midmarch", world, world.regions[1], prosperity=50)
    await keep_winds(await at(session, 3), WindTally())
    tally = SeasonTally()
    await keep_seasons(await at(session, 3, monsoons={"swing": 0, "fail_below": 150}), tally)
    season = await session.get(MonsoonSeasonRow, (world.world.id, 3))
    assert season is not None and season.failed and tally.failed == 1
    assert stat(port, "prosperity") == 50 - rules.monsoons.famine_prosperity and stat(inland, "prosperity") == 50
    hunger = await session.scalar(select(NotableYearRow).where(NotableYearRow.kind == NotableYearKind.HUNGER, NotableYearRow.world_id == world.world.id))
    assert hunger is not None
    assert await sea_navigation(session, rules, (port.id, inland.id), 3) == 1 + rules.monsoons.sea_danger_pct / 100
    season.failed, season.strength = False, 160
    assert await sea_navigation(session, rules, (port.id, inland.id), 3) == 1 - rules.monsoons.sea_danger_pct / 100


async def test_a_climate_swing_turns_its_phase_and_shifts_the_rains_of_the_warm_coasts(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    await laid_out(session, world)
    session.add(ClimateOscillationRow(world_id=world.world.id, phase=OscillationPhase.COLD, period=3, step=2, strength=12, locked=[]))
    await session.flush()
    tally = SeasonTally()
    await keep_seasons(await at(session, 3), tally)
    swing = await session.get(ClimateOscillationRow, world.world.id)
    assert swing is not None and swing.step == 0 and swing.phase is OscillationPhase.WARM and tally.turned == 1
    shifts = await clime_shifts(session, rules, 3)
    assert shifts[world.regions[0].id] == (-12, 6)
    assert shifts[world.regions[1].id] == (6, 6)


async def test_word_washes_from_one_current_coast_to_the_next(session: AsyncSession, world: CoreWorld) -> None:
    grounds = await laid_out(session, world)
    grounds[3].coast_kind = CoastKind.BEACH
    first = await settlement(session, "Brinehold", world, world.regions[0])
    second = await settlement(session, "Farshore", world, world.regions[3])
    await keep_winds(await at(session, 3), WindTally())
    assert set(await current_coasts(session)) == {(first.id, second.id), (second.id, first.id)}
    found = await links(await at(session, 3))
    assert (second.id, RumourChannel.CURRENT) in found.of(first.id)


async def test_a_physical_way_between_worlds_waits_for_its_window_but_a_bridge_does_not(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    other, _ = await add_empty_world(session)
    world.world.year_length_days, other.year_length_days = 365, 730
    session.add(RouteRow(world_a_id=world.world.id, world_b_id=other.id, method=TravelMethod.LIGHT_SAIL, duration_epochs=2, danger=10, created_epoch=1))
    await session.flush()
    tally = CrossingTally()
    await keep_windows(await at(session, 3), tally)
    key = tuple(sorted((world.world.id, other.id)))
    window = await session.get(LaunchWindowRow, key)
    assert window is not None and rules.launch_windows.synodic_min <= window.synodic <= rules.launch_windows.synodic_max and tally.windows == 1
    window.synodic, window.offset, window.open = 5, 1, False
    ends = (world.world.id, other.id)
    assert await window_delay(session, rules, TravelMethod.LIGHT_SAIL, ends, 3) == rules.launch_windows.closed_epochs
    assert await window_delay(session, rules, TravelMethod.LIGHT_SAIL, ends, 4) == 0
    assert await window_delay(session, rules, TravelMethod.DIVINE_BRIDGE, ends, 3) == 0
    window.locked = ["open"]
    window.open = True
    await keep_windows(await at(session, 3), tally)
    assert window.open


async def test_travellers_of_a_busy_road_grow_a_culture_that_pulls_their_values_and_gives_them_a_tongue(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    other, _ = await add_empty_world(session)
    first = await settlement(session, "Brinehold", world, world.regions[0])
    second = await settlement(session, "Farshore", world, world.regions[1])
    for town in (first, second):
        town.affiliated_entity_id = world.people.id
        await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
        await bond(session, town.id, world.language.id, BondKind.SPEAKS)
    session.add(CultureValueRow(entity_id=world.people.id, axis=ValueAxis.TRADITION, value=40))
    route = RouteRow(world_a_id=world.world.id, world_b_id=other.id, method=TravelMethod.LIGHT_SAIL, duration_epochs=2, danger=10, created_epoch=1, traffic=500)
    session.add(route)
    await session.flush()
    for index, town in enumerate((first, second)):
        trader = await mortal(session, f"Trader {index}", world, town.id)
        session.add(
            JourneyRow(
                traveller_entity_id=trader.id,
                route_id=route.id,
                origin_world_id=world.world.id,
                destination_world_id=other.id,
                intent=JourneyIntent.TRADE,
                epochs_left=1,
                status=JourneyStatus.UNDERWAY,
                start_epoch=2,
            )
        )
    await session.flush()
    tally = CrossingTally()
    await keep_cultures(await at(session, 3, cosmopolitan={"traffic_from": 100}), tally)
    culture = await session.scalar(select(CosmopolitanCultureRow).where(CosmopolitanCultureRow.route_id == route.id))
    assert culture is not None and culture.lingua_franca_entity_id == world.language.id and culture.values == {"tradition": 40} and tally.cultures == 1
    members = set(await session.scalars(select(CosmopolitanMemberRow.community_entity_id).where(CosmopolitanMemberRow.culture_id == culture.id)))
    assert members == {first.id, second.id}
    culture.values = {"tradition": 90}
    member = await session.get(CosmopolitanMemberRow, (culture.id, first.id))
    assert member is not None
    member.share = 100
    await keep_cultures(await at(session, 4, cosmopolitan={"traffic_from": 100, "value_pull_pct": 50, "share_gain": 0}), tally)
    value = await session.get(CultureValueRow, (world.people.id, ValueAxis.TRADITION))
    assert value is not None and value.value > 40
    native = await session.get(SpeakerCohortRow, (first.id, world.language.id, SpeakerKind.SECOND))
    assert native is not None and native.share == 100 and rules.cosmopolitan.lingua_share <= 100
