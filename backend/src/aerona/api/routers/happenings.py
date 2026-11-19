from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.happenings import (
    EventCasualtyView,
    EventSummaryView,
    EventView,
    FootprintView,
    HappeningsHereView,
    LandShapeView,
    PhaseStepView,
    RegionRef,
    RiverShiftView,
    SeasonRef,
)
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.happenings import EventCasualtyRow, EventFootprintRow, EventProfileRow, RegionGeomorphRow, RiverShiftRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.happening import EventPhase
from aerona.engine.environment.geomorph import eruption_chance
from aerona.engine.happenings.control import EVENT_KINDS
from aerona.engine.happenings.profile import MULTI_SEASON
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["happenings"])
PHASE_ORDER = (EventPhase.ONSET, EventPhase.PEAK, EventPhase.AFTERMATH, EventPhase.MEMORY)
KINDS = sorted(EVENT_KINDS, key=lambda kind: kind.value)


async def names_of(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {entity_id: name for entity_id, name in await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.id.in_(list(ids))))}


async def seasons_of(session: AsyncSession, world_id: int | None) -> list[SeasonRef]:
    if world_id is None:
        return []
    rows = await session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position))
    return [SeasonRef(position=row.position, name=row.name) for row in rows]


def season_ref(seasons: list[SeasonRef], position: int | None) -> SeasonRef | None:
    return next((season for season in seasons if season.position == position), None) if position is not None else None


def steps_of(profile: EventProfileRow | None, multi: bool) -> list[PhaseStepView]:
    phase = profile.phase if profile is not None else EventPhase.ONSET
    shown = PHASE_ORDER if multi or phase is EventPhase.PEAK else (EventPhase.ONSET, EventPhase.AFTERMATH)
    reached = PHASE_ORDER.index(phase)
    return [
        PhaseStepView(
            phase=item,
            reached=PHASE_ORDER.index(item) <= reached,
            current=item is phase and (profile is None or profile.end_epoch is None),
            since_epoch=(profile.phase_epoch if item is phase else profile.start_epoch if item is EventPhase.ONSET else None) if profile is not None else None,
        )
        for item in shown
    ]


async def event_entity(session: AsyncSession, entity_id: int) -> EntityRow:
    entity = await session.get(EntityRow, entity_id)
    if entity is None or entity.entity_type is not EntityType.EVENT:
        raise NotFoundError("No such event.")
    return entity


@router.get("/entities/{entity_id}/event", response_model=EventView)
async def event(services: ServicesDep, entity_id: int = Path(ge=1)) -> EventView:
    async with reader(services) as session:
        entity = await event_entity(session, entity_id)
        profile = await session.get(EventProfileRow, entity.id)
        footprint = list(
            await session.scalars(select(EventFootprintRow).where(EventFootprintRow.event_entity_id == entity.id).order_by(EventFootprintRow.region_entity_id))
        )
        casualties = list(
            await session.scalars(
                select(EventCasualtyRow)
                .where(EventCasualtyRow.event_entity_id == entity.id)
                .order_by(EventCasualtyRow.community_entity_id, EventCasualtyRow.phase, EventCasualtyRow.age_band, EventCasualtyRow.sex)
            )
        )
        names = await names_of(
            session,
            {
                *(row.region_entity_id for row in footprint),
                *(row.community_entity_id for row in casualties),
                *([entity.location_id] if entity.location_id is not None else []),
            },
        )
        incident = await session.get(IncidentRow, profile.incident_id) if profile is not None and profile.incident_id is not None else None
        line = await session.get(ChronicleRow, incident.chronicle_id) if incident is not None and incident.chronicle_id is not None else None
        seasons = await seasons_of(session, entity.world_id)
        multi = entity.engine_kind in MULTI_SEASON
        return EventView(
            entity_id=entity.id,
            name=entity.name,
            kind=entity.engine_kind,
            severity=stat(entity, "severity"),
            world_id=entity.world_id,
            location_id=entity.location_id,
            location=names.get(entity.location_id) if entity.location_id is not None else None,
            start_epoch=profile.start_epoch if profile is not None else entity.birth_epoch,
            start_year=profile.start_year if profile is not None else None,
            start_season=season_ref(seasons, profile.start_season if profile is not None else None),
            end_epoch=profile.end_epoch if profile is not None else None,
            end_year=profile.end_year if profile is not None else None,
            end_season=season_ref(seasons, profile.end_season if profile is not None else None),
            phase=profile.phase if profile is not None else EventPhase.ONSET,
            phase_epoch=profile.phase_epoch if profile is not None else entity.birth_epoch,
            multi_season=multi,
            ended=profile is not None and profile.end_epoch is not None,
            locked=list(profile.locked) if profile is not None else [],
            incident_id=incident.id if incident is not None else None,
            incident_text=line.text if line is not None else None,
            siege_id=profile.siege_id if profile is not None else None,
            footprint=[
                FootprintView(region_id=row.region_entity_id, region=names.get(row.region_entity_id, ""), joined_epoch=row.joined_epoch) for row in footprint
            ],
            casualties=[
                EventCasualtyView(
                    community_id=row.community_entity_id,
                    community=names.get(row.community_entity_id, ""),
                    age_band=row.age_band,
                    sex=row.sex,
                    social_class=row.social_class,
                    phase=row.phase,
                    count=row.count,
                )
                for row in casualties
            ],
            toll=sum(row.count for row in casualties),
            steps=steps_of(profile, multi),
            seasons=seasons,
            kinds=KINDS,
        )


@router.get("/entities/{entity_id}/happenings", response_model=HappeningsHereView)
async def happenings_here(services: ServicesDep, entity_id: int = Path(ge=1)) -> HappeningsHereView:
    async with reader(services) as session:
        place = await session.get(EntityRow, entity_id)
        if place is None:
            raise NotFoundError("No such record.")
        atlas = await RegionAtlas.load(session)
        region_id = place.id if place.entity_type is EntityType.REGION else atlas.top_region(place.id)
        touching = select(EventFootprintRow.event_entity_id).where(EventFootprintRow.region_entity_id == region_id) if region_id is not None else None
        clause = EntityRow.location_id == place.id
        if touching is not None and place.entity_type is EntityType.REGION:
            clause = or_(clause, EntityRow.id.in_(touching))
        events = list(
            await session.scalars(
                select(EntityRow)
                .where(EntityRow.entity_type == EntityType.EVENT, EntityRow.status != EntityStatus.REJECTED, clause)
                .order_by(EntityRow.birth_epoch.desc(), EntityRow.id.desc())
            )
        )
        ids = [row.id for row in events]
        profiles = {row.entity_id: row for row in await session.scalars(select(EventProfileRow).where(EventProfileRow.entity_id.in_(ids)))} if ids else {}
        tolls: dict[int, int] = {}
        if ids:
            for event_id, count in await session.execute(
                select(EventCasualtyRow.event_entity_id, EventCasualtyRow.count).where(EventCasualtyRow.event_entity_id.in_(ids))
            ):
                tolls[event_id] = tolls.get(event_id, 0) + count
        return HappeningsHereView(
            location_id=place.id,
            world_id=place.world_id,
            region_id=region_id,
            events=[
                EventSummaryView(
                    entity_id=row.id,
                    name=row.name,
                    kind=row.engine_kind,
                    phase=profiles[row.id].phase if row.id in profiles else EventPhase.ONSET,
                    ended=row.id in profiles and profiles[row.id].end_epoch is not None,
                    start_year=profiles[row.id].start_year if row.id in profiles else None,
                    end_year=profiles[row.id].end_year if row.id in profiles else None,
                    toll=tolls.get(row.id, 0),
                    severity=stat(row, "severity"),
                )
                for row in events
            ],
            kinds=KINDS,
            seasons=await seasons_of(session, place.world_id),
        )


@router.get("/entities/{entity_id}/land-shape", response_model=LandShapeView)
async def land_shape(services: ServicesDep, entity_id: int = Path(ge=1)) -> LandShapeView:
    async with reader(services) as session:
        region = await session.get(EntityRow, entity_id)
        if region is None or region.entity_type is not EntityType.REGION:
            raise NotFoundError("No such region.")
        rules = rules_from_snapshot((await CosmosRepository(session).require_cosmos()).rules_snapshot)
        ground = await session.get(RegionEnvironmentRow, region.id)
        shape = await session.get(RegionGeomorphRow, region.id)
        shifts = list(
            await session.scalars(
                select(RiverShiftRow)
                .where(or_(RiverShiftRow.from_region_id == region.id, RiverShiftRow.to_region_id == region.id))
                .order_by(RiverShiftRow.epoch.desc(), RiverShiftRow.id.desc())
            )
        )
        atlas = await RegionAtlas.load(session)
        neighbours = [region_id for region_id in atlas.neighbour_regions(region.id) if not atlas.is_water(region_id)]
        names = await names_of(session, {*neighbours, *(row.from_region_id for row in shifts), *(row.to_region_id for row in shifts)})
        return LandShapeView(
            region_id=region.id,
            region=region.name,
            soil=ground.soil if ground is not None else None,
            terrain=ground.dominant_terrain if ground is not None else None,
            river_class=ground.river_class if ground is not None else None,
            rainfall=ground.rainfall if ground is not None else None,
            grazed=ground.grazed if ground is not None else None,
            desertification=shape.desertification if shape is not None else 0,
            desertified=shape.desertified if shape is not None else False,
            desert_since_epoch=shape.desert_since_epoch if shape is not None else None,
            river_course=shape.river_course if shape is not None else None,
            course_changed_epoch=shape.course_changed_epoch if shape is not None else None,
            volcanic=shape.volcanic if shape is not None else False,
            volcanic_pressure=shape.volcanic_pressure if shape is not None else 0,
            eruption_chance=eruption_chance(rules, shape),
            last_eruption_epoch=shape.last_eruption_epoch if shape is not None else None,
            ash_since_epoch=shape.ash_since_epoch if shape is not None else None,
            ash_weathering_epochs=rules.geomorphology.ash_weathering_epochs,
            desertified_at=rules.geomorphology.desertified_at,
            locked=list(shape.locked) if shape is not None else [],
            soil_locked=ground is not None and "soil" in ground.locked,
            shifts=[
                RiverShiftView(
                    id=row.id,
                    from_region_id=row.from_region_id,
                    from_region=names.get(row.from_region_id, ""),
                    to_region_id=row.to_region_id,
                    to_region=names.get(row.to_region_id, ""),
                    epoch=row.epoch,
                    year=row.year,
                    river_class=row.river_class,
                    cause=row.cause,
                )
                for row in shifts
            ],
            neighbours=[
                RegionRef(region_id=region_id, region=names.get(region_id, "")) for region_id in sorted(neighbours, key=lambda item: names.get(item, ""))
            ],
        )
