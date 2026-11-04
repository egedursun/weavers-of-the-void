from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.environment import (
    AstronomyRecordView,
    CalendarView,
    ClimateAgeView,
    ForcedWeatherView,
    HolyDayView,
    LeyLineView,
    NeighbourRegion,
    NotableYearView,
    PlaceEnvironmentView,
    RegionEnvironmentView,
    SeasonView,
    WeatherForecast,
    WorldSeasonsView,
)
from aerona.catalog.climate import CLIMATES
from aerona.catalog.weather import WEATHER
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, ForcedWeatherRow, LeyLineRow, NotableYearRow, PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import LandUse
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["environment"])

FORECAST_SLOT = "forecast"


async def ley_views(session: AsyncSession, region_id: int) -> list[LeyLineView]:
    lines = list(
        await session.scalars(select(LeyLineRow).where(or_(LeyLineRow.region_a_id == region_id, LeyLineRow.region_b_id == region_id)).order_by(LeyLineRow.id))
    )
    others = {line.id: line.region_b_id if line.region_a_id == region_id else line.region_a_id for line in lines}
    names = {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(list(others.values()))))}
    return [
        LeyLineView(
            id=line.id,
            other_region_id=others[line.id],
            other_region_name=names.get(others[line.id], ""),
            strength=line.strength,
            severed=line.severed,
            severed_until_epoch=line.severed_until_epoch,
            forged=line.forged,
        )
        for line in lines
    ]


async def forced_views(session: AsyncSession, region_id: int, epoch: int) -> list[ForcedWeatherView]:
    rows = await session.scalars(
        select(ForcedWeatherRow).where(ForcedWeatherRow.region_entity_id == region_id, ForcedWeatherRow.until_epoch >= epoch).order_by(ForcedWeatherRow.id)
    )
    return [
        ForcedWeatherView(
            id=row.id,
            kind=row.kind,
            label=WEATHER[row.kind].label,
            from_epoch=row.from_epoch,
            until_epoch=row.until_epoch,
            season_position=row.season_position,
            son_id=row.son_id,
        )
        for row in rows
    ]


async def neighbour_views(session: AsyncSession, region_id: int) -> list[NeighbourRegion]:
    atlas = await RegionAtlas.load(session)
    rows = await session.scalars(select(EntityRow).where(EntityRow.id.in_(atlas.neighbour_regions(region_id))).order_by(EntityRow.name))
    return [NeighbourRegion(id=row.id, name=row.name) for row in rows]


def notable_view(row: NotableYearRow) -> NotableYearView:
    return NotableYearView(
        id=row.id,
        epoch=row.epoch,
        year=row.year,
        kind=row.kind,
        weather=row.weather,
        name=row.name,
        magnitude=row.magnitude,
        region_id=row.region_entity_id,
        legend_id=row.legend_entity_id,
    )


@router.get("/regions/{region_id}/environment", response_model=RegionEnvironmentView)
async def region_environment(services: ServicesDep, region_id: int = Path(ge=1)) -> RegionEnvironmentView:
    async with reader(services) as session:
        ground = await session.get(RegionEnvironmentRow, region_id)
        region = await session.get(EntityRow, region_id)
        if ground is None or region is None:
            raise NotFoundError("This region has not been surveyed yet.")
        cosmos = await CosmosRepository(session).require_cosmos()
        book = await EnvironmentBook.load(session, services.rules.current, cosmos.epoch)
        forecast = []
        seasons: list[WorldSeasonRow | None] = [*book.seasons_of(ground.world_id)] or [None]
        for season in seasons:
            weather = book.weather(cosmos.rng_seed, cosmos.epoch, ground, season, f"{FORECAST_SLOT}.{season.position if season else 0}")
            forecast.append(
                WeatherForecast(
                    season_id=season.id if season else None,
                    season_name=season.name if season else None,
                    kind=weather.kind,
                    label=weather.label,
                    effects=weather.effects,
                )
            )
        return RegionEnvironmentView(
            region_id=region.id,
            world_id=ground.world_id,
            surveyed=ground.surveyed,
            biome_mix=list(ground.biome_mix),
            dominant_terrain=ground.dominant_terrain,
            elevation_mean=ground.elevation_mean,
            roughness=ground.roughness,
            latitude=ground.latitude,
            moisture=ground.moisture,
            base_forest=ground.base_forest,
            forest_cover=ground.forest_cover,
            base_wetland=ground.base_wetland,
            wetland=ground.wetland,
            river_class=ground.river_class,
            coast_kind=ground.coast_kind,
            soil=ground.soil,
            soil_fertility=ground.soil_fertility,
            soil_base=ground.soil_base,
            fertility=stat(region, "fertility"),
            temperature=ground.temperature,
            temperature_band=ground.temperature_band,
            rainfall=ground.rainfall,
            seasonality=ground.seasonality,
            disease_load=ground.disease_load,
            magic_density=ground.magic_density,
            defensibility=ground.defensibility,
            passability=dict(ground.passability),
            mineral_layers=dict(ground.mineral_layers),
            scars=dict(ground.scars),
            land_use={use.value: getattr(ground, use.value) for use in LandUse},
            erosion=ground.erosion,
            harvest_pct=ground.harvest_pct,
            sacredness=ground.sacredness,
            derived_fertility=ground.derived_fertility,
            locked=list(ground.locked),
            forecast=forecast,
            ley_lines=await ley_views(session, region.id),
            forced_weather=await forced_views(session, region.id, cosmos.epoch),
            neighbours=await neighbour_views(session, region.id),
            notable_years=[
                notable_view(row)
                for row in await session.scalars(
                    select(NotableYearRow).where(NotableYearRow.region_entity_id == region.id).order_by(NotableYearRow.year.desc(), NotableYearRow.id.desc())
                )
            ],
        )


@router.get("/places/{place_id}/environment", response_model=PlaceEnvironmentView)
async def place_environment(services: ServicesDep, place_id: int = Path(ge=1)) -> PlaceEnvironmentView:
    async with reader(services) as session:
        ground = await session.get(PlaceEnvironmentRow, place_id)
        if ground is None:
            raise NotFoundError("This place has not been surveyed yet.")
        return PlaceEnvironmentView(
            place_id=ground.entity_id,
            region_id=ground.region_entity_id,
            terrain=ground.terrain,
            cover=ground.cover,
            water_source=ground.water_source,
            height_advantage=ground.height_advantage,
            chokepoint=ground.chokepoint,
            nexus=ground.nexus,
            soil_fertility=ground.soil_fertility,
        )


@router.get("/worlds/{world_id}/seasons", response_model=WorldSeasonsView)
async def world_seasons(services: ServicesDep, world_id: int = Path(ge=1)) -> WorldSeasonsView:
    async with reader(services) as session:
        world = await session.get(WorldRow, world_id)
        if world is None:
            raise NotFoundError("No such world.")
        cosmos = await CosmosRepository(session).require_cosmos()
        book = await EnvironmentBook.load(session, services.rules.current, cosmos.epoch)
        calendars = list(await session.scalars(select(CalendarRow).where(CalendarRow.world_id == world_id).order_by(CalendarRow.knowledge_entity_id)))
        names = {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_([item.knowledge_entity_id for item in calendars])))}
        notable = await session.scalars(
            select(NotableYearRow).where(NotableYearRow.world_id == world_id).order_by(NotableYearRow.year.desc(), NotableYearRow.id.desc())
        )
        climate = (
            ClimateAgeView(
                era=world.climate_era,
                label=CLIMATES[world.climate_era].label,
                description=CLIMATES[world.climate_era].description,
                since_epoch=world.climate_since_epoch,
                epochs_left=world.climate_epochs_left,
                imposed=world.climate_imposed_by_son_id is not None,
            )
            if world.climate_era is not None
            else None
        )
        kept = {calendar.knowledge_entity_id for calendar in calendars}
        astronomy = await session.scalars(
            select(EntityRow)
            .where(
                EntityRow.world_id == world_id,
                EntityRow.entity_type == EntityType.KNOWLEDGE,
                EntityRow.knowledge_branch == KnowledgeBranch.ASTRONOMY,
                EntityRow.status == EntityStatus.CANON,
            )
            .order_by(EntityRow.name)
        )
        return WorldSeasonsView(
            world_id=world.id,
            astronomy_records=[AstronomyRecordView(id=row.id, name=row.name) for row in astronomy if row.id not in kept],
            climate=climate,
            axial_tilt=world.axial_tilt,
            year_length_days=world.year_length_days,
            season_count=world.season_count,
            day_length_hours=world.day_length_hours,
            moon_count=world.moon_count,
            tidal_strength=world.tidal_strength,
            seasons=[
                SeasonView(
                    id=season.id,
                    position=season.position,
                    name=season.name,
                    temperature_shift=season.temperature_shift,
                    rain_shift=season.rain_shift,
                    growth=season.growth,
                    travel=season.travel,
                    campaign=season.campaign,
                    edited=season.edited,
                )
                for season in book.seasons_of(world.id)
            ],
            calendars=[
                CalendarView(
                    knowledge_id=calendar.knowledge_entity_id,
                    name=names.get(calendar.knowledge_entity_id, ""),
                    adopted_epoch=calendar.adopted_epoch,
                    anchor_year=calendar.anchor_year,
                    month_names=list(calendar.month_names),
                    holy_days=[HolyDayView(name=str(day.get("name", "")), year=day.get("year")) for day in calendar.holy_days],
                )
                for calendar in calendars
            ],
            notable_years=[notable_view(row) for row in notable],
        )
