from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.core.grammar import an, several, spoken
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.flora import RegionCropRow
from aerona.db.tables.forecasting import ObservationMethodRow, WeatherWorkRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.plants import PlantAnatomyRow, PlantPartRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.space_weather import SpaceWeatherEventRow, StarActivityRow, WorldFieldRow
from aerona.db.tables.water import CoastRow, LocalClimateRow, RegionCryosphereRow, SedimentFlowRow
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import top_region

RECENT_EVENTS = 3
PERCENT = 100


async def sky_world_lines(scope: Scope, world_id: int | None) -> list[str]:
    if world_id is None:
        return []
    session = scope.session
    world = await session.get(WorldRow, world_id)
    field = await session.get(WorldFieldRow, world_id)
    if world is None or field is None:
        return []
    strength = clamp_int(world.magnetism + field.shift, 0, PERCENT)
    found = [
        f"the magnetic field of {world.name} stands at {strength} of 100 and its upper air shields {field.shielding} of 100",
        f"compasses err by {field.compass_error} of 100 and the lights in its sky reach {field.aurora_reach} of the way from the poles",
    ]
    if field.reversal_left > 0:
        found.append(f"its field is turning over, for {several(field.reversal_left, 'more epoch', 'more epochs')}")
    if world.star_id is not None:
        star = await session.get(StarActivityRow, world.star_id)
        if star is not None:
            found.append(
                f"its star is {star.phase} of 100 through a cycle of {star.cycle_years} years, flaring at {star.flare_rate} and storming at {star.storm_rate}"
            )
    events = await session.scalars(
        select(SpaceWeatherEventRow)
        .where(SpaceWeatherEventRow.world_id == world_id)
        .order_by(SpaceWeatherEventRow.epoch.desc(), SpaceWeatherEventRow.id.desc())
        .limit(RECENT_EVENTS)
    )
    found.extend(f"in epoch {row.epoch} {an(spoken(row.kind))} of strength {row.strength} reached the ground at {row.dose}" for row in events)
    return found


async def mortal_sky_lines(scope: Scope, me: EntityRow) -> list[str]:
    return await sky_world_lines(scope, me.world_id)


async def son_sky_lines(scope: Scope, son: SonRow) -> list[str]:
    return await sky_world_lines(scope, son.current_world_id)


async def water_region_lines(scope: Scope, region_id: int | None) -> list[str]:
    if region_id is None:
        return []
    session = scope.session
    found: list[str] = []
    ice = await session.get(RegionCryosphereRow, region_id)
    if ice is not None:
        found.append(f"ice holds the waters for {several(ice.ice_months, 'month', 'months')} a year, the ground is frozen to {ice.frozen_depth} of 100")
        found.append(f"snow lies at {ice.snowpack} of 100 and glaciers cover {ice.glacier_extent} of 100 of the land")
    coast = await session.get(CoastRow, region_id)
    if coast is not None:
        movement = "builds out" if coast.rate > 0 else "wears away" if coast.rate < 0 else "holds"
        found.append(f"the coast is {an(spoken(coast.form))} that {movement}, its harbour silted to {coast.harbour_silting} of 100")
    laid_bare = (FossilBedRow.region_entity_id == region_id, FossilBedRow.found_epoch.is_not(None))
    beds = await session.scalars(select(FossilBedRow).where(*laid_bare).order_by(FossilBedRow.id).limit(RECENT_EVENTS))
    found.extend(f"bed of remains #{bed.id} lies laid bare, kept in {spoken(bed.preservation)} at a richness of {bed.richness}" for bed in beds)
    flows = await session.scalars(select(SedimentFlowRow).where(SedimentFlowRow.sink_region_id == region_id).order_by(SedimentFlowRow.id))
    found.extend(f"{spoken(row.kind)} comes in by {spoken(row.carrier)} at a load of {row.load}" for row in flows)
    return found


async def mortal_water_lines(scope: Scope, me: EntityRow) -> list[str]:
    region = await top_region(scope.session, me)
    lines = await water_region_lines(scope, region.id if region is not None else None)
    warmth = await scope.session.get(LocalClimateRow, me.location_id) if me.location_id is not None else None
    if warmth is not None:
        lines.append(f"your town shifts its own warmth by {warmth.heat_shift} and its damp by {warmth.humidity_shift}")
    return lines


async def son_water_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    rows = await scope.session.execute(
        select(RegionCryosphereRow.ice_months, EntityRow.name)
        .join(EntityRow, EntityRow.id == RegionCryosphereRow.region_entity_id)
        .where(EntityRow.world_id == son.current_world_id, RegionCryosphereRow.ice_months > 0)
        .order_by(RegionCryosphereRow.ice_months.desc(), RegionCryosphereRow.region_entity_id)
        .limit(RECENT_EVENTS)
    )
    return [f"ice holds the waters of {name} for {several(months, 'month', 'months')} a year" for months, name in rows]


async def mortal_plant_lines(scope: Scope, me: EntityRow) -> list[str]:
    region = await top_region(scope.session, me)
    if region is None:
        return []
    found: list[str] = []
    crops = await scope.session.execute(
        select(RegionCropRow.share, PlantAnatomyRow, EntityRow.name)
        .join(PlantAnatomyRow, PlantAnatomyRow.species_entity_id == RegionCropRow.plant_entity_id)
        .join(EntityRow, EntityRow.id == RegionCropRow.plant_entity_id)
        .where(RegionCropRow.region_entity_id == region.id)
        .order_by(RegionCropRow.share.desc(), RegionCropRow.plant_entity_id)
        .limit(RECENT_EVENTS)
    )
    for share, anatomy, name in crops:
        parts = await scope.session.scalars(
            select(PlantPartRow.part).where(PlantPartRow.species_entity_id == anatomy.species_entity_id).order_by(PlantPartRow.id)
        )
        given = ", ".join(spoken(part) for part in parts)
        wait = f", first harvest after {several(anatomy.first_harvest_years, 'year', 'years')}" if anatomy.first_harvest_years else ""
        found.append(f"{name} grows on {share} of your fields as {an(spoken(anatomy.form))}{wait}; its parts: {given}")
    return found


async def mortal_forecast_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    folk = await people_of(session, me)
    found: list[str] = []
    if folk is not None:
        ways = await session.scalars(select(ObservationMethodRow).where(ObservationMethodRow.people_entity_id == folk.id).order_by(ObservationMethodRow.id))
        found.extend(f"your people read the {spoken(row.domain)} by {spoken(row.method)}, at an accuracy of {row.accuracy}" for row in ways)
    region = await top_region(session, me)
    if region is not None:
        works = await session.scalars(
            select(WeatherWorkRow).where(WeatherWorkRow.region_entity_id == region.id, WeatherWorkRow.epochs_left > 0).order_by(WeatherWorkRow.id)
        )
        found.extend(f"a work turns the weather of your land toward {spoken(row.aim)}, at a strength of {row.strength}" for row in works)
    return found
