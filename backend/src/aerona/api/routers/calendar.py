from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.calendar import (
    CalendarDetail,
    FestivalEntry,
    FestivalYearView,
    HolyDayDetail,
    LeyWorkView,
    RegionWorksView,
    SeasonTradition,
    SettlementWorks,
    WorldCalendarView,
)
from aerona.api.schemas.environment import SeasonView
from aerona.api.views.culture_cards import slot_state
from aerona.catalog.lore import SLEEP_CUSTOMS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, RegionEnvironmentRow, StructureLeyRow, WorldSeasonRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import DistrictKind
from aerona.engine.environment.profile import Works, irrigation_pct
from aerona.engine.environment.season_shape import season_phase
from aerona.engine.environment.works import region_works
from aerona.engine.lore.calendar_rites import keepers_of, long_days
from aerona.engine.lore.calendar_slots import festivals_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["environment"])


async def _names(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(list(ids))))}


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


@router.get("/worlds/{world_id}/calendar", response_model=WorldCalendarView)
async def world_calendar(services: ServicesDep, world_id: int = Path(ge=1)) -> WorldCalendarView:
    async with reader(services) as session:
        world = await session.get(WorldRow, world_id)
        if world is None:
            raise NotFoundError("No such world.")
        rules = services.rules.current
        calendars = list(await session.scalars(select(CalendarRow).where(CalendarRow.world_id == world_id).order_by(CalendarRow.knowledge_entity_id)))
        traditions = list(
            await session.scalars(
                select(EntityRow)
                .where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.TRADITION, EntityRow.status == EntityStatus.CANON)
                .order_by(EntityRow.name)
            )
        )
        profiles = {
            row.tradition_entity_id: row
            for row in await session.scalars(select(TraditionProfileRow).where(TraditionProfileRow.tradition_entity_id.in_([item.id for item in traditions])))
        }
        linked = {_int(day.get("tradition_entity_id")) for calendar in calendars for day in calendar.holy_days}
        names = await _names(session, {calendar.knowledge_entity_id for calendar in calendars} | {item for item in linked if item is not None})
        details = [
            CalendarDetail(
                knowledge_id=calendar.knowledge_entity_id,
                name=names.get(calendar.knowledge_entity_id, ""),
                anchor_year=calendar.anchor_year,
                keepers=len(await keepers_of(session, calendar.knowledge_entity_id)),
                holy_days=[
                    HolyDayDetail(
                        index=index,
                        name=str(day.get("name", "")),
                        year=_int(day.get("year")),
                        season_position=_int(day.get("season_position")),
                        notable_year_id=_int(day.get("notable_year_id")),
                        tradition_id=_int(day.get("tradition_entity_id")),
                        tradition_name=names.get(_int(day.get("tradition_entity_id")) or 0),
                    )
                    for index, day in enumerate(calendar.holy_days)
                ],
            )
            for calendar in calendars
        ]
        views = [
            SeasonTradition(
                id=item.id,
                name=item.name,
                kind=profile.kind,
                season_position=profile.season_position,
                calendar_id=profile.calendar_entity_id,
                calendar_name=names.get(profile.calendar_entity_id or 0),
                in_season=profile.in_season,
                held=[key for key in profile.locked if key in {"season_position", "calendar_entity_id"}],
            )
            for item in traditions
            if (profile := profiles.get(item.id)) is not None
        ]
        return WorldCalendarView(
            world_id=world.id,
            calendar_locked=list(world.calendar_locked),
            day_length_hours=world.day_length_hours,
            long_days=long_days(rules.seasonal.long_day_hours, world),
            long_day_hours=rules.seasonal.long_day_hours,
            sleep_customs=sum(1 for view in views if view.kind in SLEEP_CUSTOMS),
            calendars=details,
            traditions=views,
        )


FESTIVAL_HELD = frozenset({"season_position", "calendar_slot"})


@router.get("/peoples/{people_id}/festival-year", response_model=FestivalYearView)
async def festival_year(services: ServicesDep, people_id: int = Path(ge=1)) -> FestivalYearView:
    async with reader(services) as session:
        people = await session.get(EntityRow, people_id)
        if people is None or people.entity_type is not EntityType.PEOPLE:
            raise NotFoundError("No such people.")
        seasons = list(await session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == people.world_id).order_by(WorldSeasonRow.position)))
        phases = season_phase(seasons)
        festivals = []
        for tradition, profile in await festivals_of(session, people.id):
            state = await slot_state(session, profile, people.id)
            festivals.append(
                FestivalEntry(
                    id=tradition.id,
                    name=tradition.name,
                    kind=profile.kind,
                    calendar_slot=profile.calendar_slot,
                    season_position=profile.season_position,
                    in_season=profile.in_season,
                    slot_open=state.open if state is not None else None,
                    slot_reason=state.reason if state is not None else None,
                    held=sorted(key for key in profile.locked if key in FESTIVAL_HELD),
                )
            )
        return FestivalYearView(
            people_id=people.id,
            world_id=people.world_id,
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
                    share_pct=season.share_pct,
                    warmth=phases[season.position].warmth,
                    water=phases[season.position].water,
                    edited=season.edited,
                )
                for season in seasons
            ],
            festivals=festivals,
        )


@router.get("/regions/{region_id}/works", response_model=RegionWorksView)
async def region_works_view(services: ServicesDep, region_id: int = Path(ge=1)) -> RegionWorksView:
    async with reader(services) as session:
        ground = await session.get(RegionEnvironmentRow, region_id)
        if ground is None:
            raise NotFoundError("This region has not been surveyed yet.")
        rules = services.rules.current
        atlas = await RegionAtlas.load(session)
        works = (await region_works(session, atlas, rules)).get(region_id)
        here = [
            entity
            for entity in await session.scalars(
                select(EntityRow).where(EntityRow.world_id == ground.world_id, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.name)
            )
            if entity.entity_type in {EntityType.SETTLEMENT, EntityType.STRUCTURE} and atlas.top_region(entity.id) == region_id
        ]
        settlements = [entity for entity in here if entity.entity_type is EntityType.SETTLEMENT]
        infrastructure = {
            row.settlement_entity_id: row
            for row in await session.scalars(
                select(SettlementInfrastructureRow).where(SettlementInfrastructureRow.settlement_entity_id.in_([item.id for item in settlements]))
            )
        }
        harboured = set(
            await session.scalars(
                select(DistrictRow.settlement_entity_id).where(
                    DistrictRow.kind == DistrictKind.HARBOUR, DistrictRow.settlement_entity_id.in_([item.id for item in settlements])
                )
            )
        )
        structures = [entity for entity in here if entity.entity_type is EntityType.STRUCTURE]
        ley = {
            row.structure_entity_id: row
            for row in await session.scalars(select(StructureLeyRow).where(StructureLeyRow.structure_entity_id.in_([item.id for item in structures])))
        }
        lost = round(ground.base_forest * ground.cleared / PERCENT * rules.environment.forest_rain_pct / PERCENT)
        return RegionWorksView(
            region_id=region_id,
            roads=works.roads if works is not None else 0,
            bridges=works.bridges if works is not None else 0,
            harbours=works.harbours if works is not None else 0,
            irrigation=works.irrigation if works is not None else 0,
            irrigation_pct=irrigation_pct(rules, ground.river_class, works) if works is not None else irrigation_pct(rules, ground.river_class, Works()),
            rainfall=ground.rainfall,
            rain_lost_to_clearing=lost,
            cleared=ground.cleared,
            settlements=[
                SettlementWorks(
                    settlement_id=item.id,
                    name=item.name,
                    bridges=row.bridges if (row := infrastructure.get(item.id)) is not None else 0,
                    irrigation=row.irrigation if row is not None else 0,
                    harbour=item.id in harboured,
                    locked=[key for key in (row.locked if row is not None else []) if key in {"bridges", "irrigation"}],
                )
                for item in settlements
            ],
            ley_works=[
                LeyWorkView(
                    structure_id=item.id,
                    name=item.name,
                    attuned=tie.attuned if (tie := ley.get(item.id)) is not None else False,
                    on_ley_line=tie.on_ley_line if tie is not None else False,
                    at_nexus=tie.at_nexus if tie is not None else False,
                    function=stat(item, "function"),
                    locked=list(tie.locked) if tie is not None else [],
                )
                for item in structures
            ],
        )
