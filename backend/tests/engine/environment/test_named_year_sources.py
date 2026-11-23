from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.named_years import NAMED_YEARS, year_name
from aerona.catalog.weather import WEATHER
from aerona.db.tables.ages import IrregularSeasonRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.environment import NotableYearRow, RegionEnvironmentRow
from aerona.domain.enums.ages import SeasonCause, SeasonSpellShape
from aerona.domain.enums.culture import CalendarSlot
from aerona.domain.enums.environment import NotableYearKind, WeatherKind, WeatherTrait
from aerona.engine.agrarian.book import famine_cushions, intensities
from aerona.engine.ecology.flora import CropBook
from aerona.engine.ecology.keystones import services_by_region
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.notable import spell_years
from aerona.engine.lore.traditions import remember_years
from aerona.engine.phases.environment import HarvestSeason, YearHarvest, weather_year
from aerona.engine.primitives.capacity import LAND_COMMUNITY_TYPES, CapacityModel
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import canon
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, settlement, surveyed, tuned_rules

RULES = Rules()
Y = NotableYearKind


def test_every_kind_names_its_year_from_one_catalogue() -> None:
    assert set(NAMED_YEARS) == set(NotableYearKind)
    assert year_name(Y.WEATHER, "Low Fen", WEATHER[WeatherKind.FROST].label) == f"the Year of {WEATHER[WeatherKind.FROST].label} in Low Fen"
    assert year_name(Y.OMEN, "Low Fen") == "the Year of the Sign in Low Fen"
    assert WeatherTrait.EXTREME in WEATHER[WeatherKind.FROST].traits and WeatherTrait.EXTREME in WEATHER[WeatherKind.ICE_STORM].traits


async def test_the_first_year_of_a_single_long_season_is_named_by_its_cause(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    ctx = await manual_context(session, "test", RULES)
    for region, cause, shape in (
        (world.regions[0], SeasonCause.IMPACT, SeasonSpellShape.SINGLE),
        (world.regions[1], SeasonCause.STELLAR, SeasonSpellShape.SINGLE),
        (world.regions[2], SeasonCause.ERUPTION, SeasonSpellShape.CYCLING),
    ):
        session.add(
            IrregularSeasonRow(
                world_id=world.world.id, cause=cause, shape=shape, spell_started_epoch=ctx.epoch, severity=70, source_region_id=region.id, locked=[]
            )
        )
    await session.flush()
    assert await spell_years(ctx, await RegionAtlas.load(session)) == 2
    await session.flush()
    named = {(row.region_entity_id, row.kind, row.magnitude) for row in await session.scalars(select(NotableYearRow))}
    assert named == {(world.regions[0].id, Y.DISASTER, 70), (world.regions[1].id, Y.OMEN, 70)}


async def test_a_frost_year_is_named_as_a_weather_year(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", RULES)
    book = await EnvironmentBook.load(session, RULES, ctx.epoch)
    loads = (await CapacityModel.load(session, RULES)).build_loads(await canon(session, LAND_COMMUNITY_TYPES))
    season = HarvestSeason(
        book,
        loads,
        await KnowledgeMap.load(session),
        set(),
        None,
        [],
        await CropBook.load(session, RULES, book.regions),
        {},
        await services_by_region(session),
        await intensities(session),
        await famine_cushions(session, book.atlas),
    )
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    row = await session.get(WorldRow, world.world.id)
    assert land is not None and row is not None
    season.worst_weather = (RULES.named_years.weather_growth_min - 1, YearHarvest(0, 10, 60, WeatherKind.FROST), land)
    assert await weather_year(ctx, row, season) == 0
    season.worst_weather = (RULES.named_years.weather_growth_min, YearHarvest(0, 10, 60, WeatherKind.FROST), land)
    assert await weather_year(ctx, row, season) == 1
    await session.flush()
    year = await session.scalar(select(NotableYearRow))
    assert year is not None and year.kind is Y.WEATHER and year.weather is WeatherKind.FROST and WEATHER[WeatherKind.FROST].label in year.name


async def test_a_people_remembers_any_named_year_that_reaches_its_threshold(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await settlement(session, "Keepers", world, world.regions[0])
    ctx = await manual_context(session, "test", tuned_rules(traditions={"commemoration_chance": 100, "commemoration_keepers": 100}))
    need = RULES.named_years.remembered_magnitude_pestilence
    for kind, magnitude in ((Y.PESTILENCE, need), (Y.DISCOVERY, RULES.named_years.remembered_magnitude_discovery - 1)):
        session.add(
            NotableYearRow(
                world_id=world.world.id,
                region_entity_id=world.regions[0].id,
                epoch=ctx.epoch,
                year=5,
                kind=kind,
                weather=None,
                name=year_name(kind, world.regions[0].name),
                magnitude=magnitude,
            )
        )
    await session.flush()
    founded = await remember_years(ctx, await RegionAtlas.load(session))
    assert len(founded) == 1
    profile = await session.get(TraditionProfileRow, founded[0].id)
    remembered = await session.scalar(select(NotableYearRow).where(NotableYearRow.kind == Y.PESTILENCE))
    assert profile is not None and remembered is not None
    assert profile.calendar_slot is CalendarSlot.REMEMBRANCE and profile.notable_year_id == remembered.id
