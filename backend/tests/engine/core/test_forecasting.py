from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.climes import MonsoonSeasonRow
from aerona.db.tables.cosmography import CelestialReadingRow
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.environment import ForcedWeatherRow
from aerona.db.tables.forecasting import ObservationMethodRow, WeatherWorkRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.cosmography import OmenReading
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.forecasting import ObservationMethod, WeatherAim, WeatherWorkMethod
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import CelestialStats
from aerona.engine.context import TickContext
from aerona.engine.forecasting.reading import sky_marks, sky_omens
from aerona.engine.forecasting.works import ForecastTally, keep_forecasting
from tests.engine.core.factories import CoreWorld, entity, settlement, surveyed


async def test_every_people_reads_the_weather_by_sight_at_least(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await keep_forecasting(ctx, ForecastTally())
    ways = set(await session.scalars(select(ObservationMethodRow.method).where(ObservationMethodRow.people_entity_id == world.people.id)))
    assert ObservationMethod.SIGHT in ways


async def test_a_true_reading_foresees_a_failed_monsoon(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(ObservationMethodRow(people_entity_id=world.people.id, domain=FolkDomain.WEATHER, method=ObservationMethod.ALMANAC, accuracy=90, locked=[]))
    session.add(MonsoonSeasonRow(world_id=world.world.id, epoch=ctx.epoch, strength=10, failed=True, locked=[]))
    await session.flush()
    await keep_forecasting(ctx, ForecastTally())
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "weather.forecast_kept")) is not None


async def test_a_weather_work_holds_its_weather_and_turns_the_land_downwind(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    first, second = world.regions[0].id, world.regions[1].id
    session.add(
        WeatherWorkRow(
            holder_node_id=world.people.id,
            region_entity_id=first,
            downwind_region_id=second,
            method=WeatherWorkMethod.RITE,
            aim=WeatherAim.RAIN,
            strength=60,
            epochs_left=2,
            locked=[],
        )
    )
    await session.flush()
    await keep_forecasting(ctx, ForecastTally())
    held = {row.region_entity_id: row.kind.value for row in await session.scalars(select(ForcedWeatherRow))}
    assert held.get(first) == "rain" and held.get(second) == "drought_wind"
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "weather.side_effect")) is not None


async def test_a_people_that_watches_the_heavens_reads_the_sky_better(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    table = ctx.rules.forecasting
    assert await sky_marks(session, ctx.rules, world.people.id) == 0
    bodies = [await entity(session, f"Body {number}", EntityType.CELESTIAL, CelestialStats(), world_id=world.world.id) for number in range(10)]
    session.add_all(
        CelestialReadingRow(
            celestial_entity_id=body.id, people_entity_id=world.people.id, reading=OmenReading.GOOD, visible=number % 2 == 0, epoch=1, locked=[]
        )
        for number, body in enumerate(bodies)
    )
    await session.flush()
    assert await sky_marks(session, ctx.rules, world.people.id) == min(table.sky_mark_cap, 5 * table.sky_mark_accuracy)


async def test_good_and_evil_omens_in_a_people_s_sky_weigh_against_each_other(session: AsyncSession, world: CoreWorld) -> None:
    readings = (OmenReading.GOOD, OmenReading.GOOD, OmenReading.GOOD, OmenReading.EVIL, OmenReading.NEUTRAL)
    bodies = [await entity(session, f"Omen {number}", EntityType.CELESTIAL, CelestialStats(), world_id=world.world.id) for number in range(len(readings))]
    session.add_all(
        CelestialReadingRow(celestial_entity_id=body.id, people_entity_id=world.people.id, reading=reading, epoch=1, locked=[])
        for body, reading in zip(bodies, readings, strict=True)
    )
    await session.flush()
    assert await sky_omens(session, world.people.id) == 2


async def test_a_town_parched_by_a_failed_monsoon_works_the_weather_toward_rain_by_what_it_knows(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    await surveyed(session, world)
    town = await settlement(session, "Dryford", world, world.regions[0], population=3000)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=500, locked=[]))
    session.add(HolderLevelRow(holder_entity_id=town.id, branch=KnowledgeBranch.AGRICULTURE, level=2))
    session.add(MonsoonSeasonRow(world_id=world.world.id, epoch=ctx.epoch, strength=10, failed=True, locked=[]))
    await session.flush()
    tally = ForecastTally()
    await keep_forecasting(ctx, tally)
    work = await session.scalar(select(WeatherWorkRow).where(WeatherWorkRow.holder_node_id == town.id))
    assert tally.raised == 1 and work is not None and work.aim is WeatherAim.RAIN and work.method is WeatherWorkMethod.SEEDING
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "weather.work_raised")) is not None
