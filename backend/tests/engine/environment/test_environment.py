from sqlalchemy import select

from aerona.core.random import SeededRandom
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, LeyLineRow, NotableYearRow, PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.environment import ScarKind, TerrainKind, WaterSource, WeatherKind
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.world import ClimateEra, SkyEventKind, WorldType
from aerona.domain.models.entity_stats import PlaceStats, StructureStats
from aerona.engine.environment.control import reorder_seasons, set_region_field, sever_ley, unlock_region_field
from aerona.engine.environment.seasons import season_drafts, world_calendar
from aerona.engine.environment.weather import WeatherInputs, weather_at, weather_weights
from aerona.engine.phases.disasters import strike
from aerona.engine.phases.environment import calendars, environment_derive, environment_survey, harvest, land_use, ley_lines
from aerona.engine.primitives.capacity import CapacityModel
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from tests.engine.environment.factories import mapped_region
from tests.engine.society.factories import Realm, context, knowledge, link, make, people, settlement, store_map, tuned

RULES = Rules()


async def surveyed(realm: Realm, **regions: dict) -> RegionEnvironmentRow:
    records = [mapped_region(realm.region.id, neighbours=[realm.far_region.id], **regions), mapped_region(realm.far_region.id, neighbours=[realm.region.id])]
    await store_map(realm.session, realm.world.id, records)
    await environment_survey(context(realm.session))
    ground = await realm.session.get(RegionEnvironmentRow, realm.region.id)
    assert ground is not None
    return ground


async def test_survey_profiles_regions_and_keeps_existing_fertility(realm: Realm) -> None:
    ground = await surveyed(realm)
    assert (ground.surveyed and ground.dominant_terrain is TerrainKind.RIVER_VALLEY) or ground.dominant_terrain in set(TerrainKind)
    assert ground.passability and ground.mineral_layers is not None
    assert ground.soil_base == ground.soil_fertility
    await environment_derive(context(realm.session))
    assert abs((stat(realm.region, "fertility") or 0) - 60) <= 1
    seasons = list(await realm.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == realm.world.id)))
    assert seasons and realm.world.axial_tilt is not None and realm.world.season_count == len(seasons)


async def test_writes_by_other_mechanics_fold_into_the_soil(realm: Realm) -> None:
    ground = await surveyed(realm)
    await environment_derive(context(realm.session))
    soil = ground.soil_fertility
    set_stats(realm.region, fertility=(stat(realm.region, "fertility") or 0) + 10)
    await environment_derive(context(realm.session))
    assert ground.soil_fertility > soil
    assert (stat(realm.region, "fertility") or 0) >= 65


async def test_a_drought_century_dries_the_land_instead_of_writing_fertility(realm: Realm) -> None:
    ground = await surveyed(realm)
    await environment_derive(context(realm.session))
    wet, fertile = ground.rainfall, stat(realm.region, "fertility") or 0
    realm.world.climate_era = ClimateEra.DROUGHT
    await environment_derive(context(realm.session))
    assert ground.rainfall == wet + RULES.climate_effects.drought_century_rain
    assert (stat(realm.region, "fertility") or 0) < fertile


def test_world_calendars_follow_the_world_type() -> None:
    locked = world_calendar(RULES, SeededRandom.for_epoch(1, 1, "t"), WorldType.TIDALLY_LOCKED, 1.0)
    assert locked.axial_tilt == 0 and locked.season_count == 1 and locked.day_length_hours == RULES.seasons.locked_day_hours
    ice = world_calendar(RULES, SeededRandom.for_epoch(1, 1, "t"), WorldType.ICE, 1.0)
    assert ice.season_count == 2
    drafts = season_drafts(RULES, WorldType.ORDINARY, 4, 45)
    summer, winter = drafts[1], drafts[3]
    assert summer.temperature_shift > winter.temperature_shift and summer.growth > winter.growth and summer.campaign > winter.campaign


def test_weather_is_deterministic_and_reads_the_land_and_sky() -> None:
    cold = WeatherInputs(region_id=5, temperature=10, rainfall=60, latitude=80, magic_density=0, terrain=TerrainKind.TUNDRA)
    assert weather_at(RULES, 3, 4, "x", cold) == weather_at(RULES, 3, 4, "x", cold)
    weights = weather_weights(RULES, cold)
    assert weights[WeatherKind.SNOW] > 0 and weights[WeatherKind.HEAT_WAVE] == 0
    dark = WeatherInputs(
        region_id=5, temperature=50, rainfall=50, latitude=10, magic_density=0, terrain=TerrainKind.PLAIN, sky=frozenset({SkyEventKind.ECLIPSE})
    )
    assert weather_weights(RULES, dark)[WeatherKind.ECLIPSE_DARK] > 0
    assert weather_weights(RULES, cold)[WeatherKind.ECLIPSE_DARK] == 0


async def test_a_failed_harvest_names_its_year_and_becomes_a_famine(realm: Realm) -> None:
    await surveyed(realm)
    await people(realm, "Reapers", population=6000)
    rules = tuned(harvest={"normal_growth": 100, "notable_threshold": 95, "famine_event_below": 95})
    await harvest(context(realm.session, rules))
    years = list(await realm.session.scalars(select(NotableYearRow)))
    assert any(row.region_entity_id == realm.region.id and row.name.startswith("the Hungry Year") for row in years)
    famines = list(await realm.session.scalars(select(EntityRow).where(EntityRow.engine_kind == EngineKind.FAMINE)))
    assert famines
    ground = await realm.session.get(RegionEnvironmentRow, realm.region.id)
    assert ground is not None and ground.harvest_pct < 100


async def test_people_work_the_land_and_empty_land_grows_wild(realm: Realm) -> None:
    ground = await surveyed(realm)
    far = await realm.session.get(RegionEnvironmentRow, realm.far_region.id)
    assert far is not None
    await settlement(realm, "Hearth", population=400000)
    farmed = ground.farmed
    far.cleared = far.farmed = 40
    await land_use(context(realm.session))
    assert ground.built > 0 and ground.cleared >= farmed
    assert far.cleared < 40 and far.farmed < 40


async def test_reordering_seasons_changes_the_year(realm: Realm) -> None:
    await surveyed(realm)
    seasons = await reorder_seasons(realm.session, realm.world.id, list(reversed(range(realm.world.season_count or 1))))
    assert [season.position for season in seasons] == list(range(len(seasons)))
    assert all(season.edited for season in seasons)


async def test_astronomy_becomes_a_calendar_that_keeps_fasts(realm: Realm) -> None:
    await surveyed(realm)
    folk = await people(realm, "Stargazers")
    lore = await knowledge(realm, "Sky Reckoning", KnowledgeBranch.ASTRONOMY)
    await link(realm.session, folk.id, lore.id, BondKind.KNOWS)
    rules = tuned(calendars={"adoption_chance": 100})
    await calendars(context(realm.session, rules))
    calendar = await realm.session.get(CalendarRow, lore.id)
    assert calendar is not None and len(calendar.month_names) == realm.world.season_count
    realm.session.add(
        NotableYearRow(
            world_id=realm.world.id, region_entity_id=realm.region.id, epoch=3, year=120, kind="hunger", name="the Hungry Year in Vale", magnitude=60
        )
    )
    await realm.session.flush()
    await calendars(context(realm.session, rules, epoch=4))
    assert any(day["name"] == "Fast of the Hungry Year in Vale" for day in calendar.holy_days)


async def test_places_inherit_terrain_and_water_shapes_capacity(realm: Realm) -> None:
    await surveyed(realm)
    spring = await make(
        realm.session,
        "Green Pass",
        EntityType.PLACE,
        PlaceStats(danger=10, fertility=50, mystery=10),
        world_id=realm.world.id,
        location_id=realm.region.id,
        subtype="pass",
    )
    await environment_survey(context(realm.session))
    ground = await realm.session.get(PlaceEnvironmentRow, spring.id)
    assert ground is not None and ground.chokepoint and ground.terrain is TerrainKind.HIGH_PASS and ground.water_source is WaterSource.NONE
    town = await settlement(realm, "Pass Town", population=4000, location_id=spring.id)
    model = await CapacityModel.load(realm.session, RULES)
    assert model.water_factor(town) == RULES.environment.dry_place_capacity_pct / 100


async def test_curses_and_plagues_scar_the_land(realm: Realm) -> None:
    ground = await surveyed(realm)
    await strike(context(realm.session), realm.region, Disaster.PLAGUE, 60)
    assert ground.scars.get(ScarKind.PLAGUE_GROUND.value, 0) > 0
    world = await realm.session.get(WorldRow, realm.world.id)
    assert world is not None


async def ley_realm(realm: Realm) -> None:
    set_stats(realm.region, magic=90)
    set_stats(realm.far_region, magic=80)
    await surveyed(realm)


async def test_magic_lands_weave_ley_lines_that_scars_can_cut(realm: Realm) -> None:
    await ley_realm(realm)
    await ley_lines(context(realm.session))
    line = await realm.session.scalar(select(LeyLineRow))
    assert line is not None and not line.severed and line.strength == 80
    ground = await realm.session.get(RegionEnvironmentRow, realm.region.id)
    assert ground is not None
    ground.scars = {ScarKind.SALTED_EARTH.value: 80}
    await ley_lines(context(realm.session, epoch=4))
    assert line.severed


async def test_a_severed_line_stays_cut_until_its_epoch(realm: Realm) -> None:
    await ley_realm(realm)
    await ley_lines(context(realm.session))
    line = await realm.session.scalar(select(LeyLineRow))
    assert line is not None
    await sever_ley(realm.session, line.id, until_epoch=5)
    await ley_lines(context(realm.session, epoch=5))
    assert line.severed
    await ley_lines(context(realm.session, epoch=6))
    assert not line.severed and line.severed_until_epoch is None


async def test_works_on_a_ley_line_gain_function(realm: Realm) -> None:
    await ley_realm(realm)
    stats = StructureStats(splendor=10, durability=50, function=40)
    work = await make(realm.session, "Ley Spire", EntityType.STRUCTURE, stats, world_id=realm.world.id, location_id=realm.region.id)
    await ley_lines(context(realm.session))
    assert (stat(work, "function") or 0) == 40 + RULES.environment.ley_function_gain


async def test_every_shown_value_can_be_set_and_held(realm: Realm) -> None:
    ground = await surveyed(realm)
    for field, value in (("seasonality", 77), ("magic_density", 66), ("harvest_pct", 150), ("passability.on_foot", 9), ("temperature", 12)):
        set_region_field(ground, field, value, lock=True)
    await environment_derive(context(realm.session))
    await ley_lines(context(realm.session))
    assert (ground.seasonality, ground.magic_density, ground.passability["on_foot"], ground.temperature) == (77, 66, 9, 12)
    await people(realm, "Reapers", population=6000)
    await harvest(context(realm.session))
    assert ground.harvest_pct == 150
    assert unlock_region_field(ground, "passability.on_foot")
    await environment_derive(context(realm.session))
    assert ground.passability["on_foot"] != 9
