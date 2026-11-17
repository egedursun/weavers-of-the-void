from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.record_context import current_scope
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.happenings import EventCasualtyRow, EventFootprintRow, EventProfileRow, RegionGeomorphRow
from aerona.domain.enums.demography import AgeBand, Sex
from aerona.domain.enums.entity import LOCATION_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.happening import EventPhase
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.context import TickContext
from aerona.engine.environment.geomorph import SHAPE_FIELDS, desert_terrain, shape_of
from aerona.engine.happenings.effects import onset
from aerona.engine.happenings.profile import add_footprint, close_profile, open_profile, region_of
from aerona.engine.happenings.progression import turn
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats
from aerona.engine.recording.record import StepDraft, record

EVENT_KINDS = ENTITY_TYPES[EntityType.EVENT].engine_kinds
PROFILE_FIELDS = frozenset({"start_year", "start_season", "end_year", "end_season", "phase"})


@dataclass(frozen=True)
class EventDraft:
    kind: EngineKind
    name: str
    where_id: int
    severity: int
    description: str = ""
    phase: EventPhase = EventPhase.ONSET
    start_year: int | None = None
    start_season: int | None = None
    footprint: Sequence[int] = ()
    partner_id: int | None = None
    hold_phase: bool = False


async def require_event(ctx: TickContext, event_id: int) -> tuple[EntityRow, EventProfileRow]:
    event = await ctx.session.get(EntityRow, event_id)
    if event is None or event.entity_type is not EntityType.EVENT:
        raise NotFoundError("No such event.")
    return event, await open_profile(ctx, event)


async def require_region(ctx: TickContext, region_id: int) -> EntityRow:
    region = await ctx.session.get(EntityRow, region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        raise NotFoundError("No such region.")
    return region


async def check_season(ctx: TickContext, world_id: int | None, position: int | None) -> int | None:
    if position is None:
        return None
    found = await ctx.session.scalar(select(WorldSeasonRow.id).where(WorldSeasonRow.world_id == world_id, WorldSeasonRow.position == position))
    if found is None:
        raise ValidationFailedError("That world has no such season.")
    return position


def hold(profile: EventProfileRow | RegionGeomorphRow, field: str, held: bool) -> None:
    locked = set(profile.locked)
    if held:
        locked.add(field)
    else:
        locked.discard(field)
    profile.locked = sorted(locked)


async def create_event(ctx: TickContext, draft: EventDraft) -> tuple[EntityRow, EventProfileRow]:
    if draft.kind not in EVENT_KINDS:
        raise ValidationFailedError(f"{spoken(draft.kind)} is not a kind of event.")
    where = await ctx.session.get(EntityRow, draft.where_id)
    if where is None or where.status is not EntityStatus.CANON:
        raise NotFoundError("No such place for the event.")
    atlas = await RegionAtlas.load(ctx.session)
    name = draft.name.strip() or f"the {spoken(draft.kind).title()} of {where.name}"
    event = await create_record(
        ctx,
        RecordSpec(
            name=name[:1].upper() + name[1:],
            entity_type=EntityType.EVENT,
            stats=EventStats(severity=clamp_int(draft.severity, 0, PERCENT)),
            body=draft.description.strip() or f"{name[:1].upper() + name[1:]}, set down by the Creator's hand.",
            power=ctx.rules.events.event_power,
            world_id=where.world_id,
            location_id=where.id if where.entity_type in LOCATION_TYPES else where.location_id,
            subtype=draft.kind.value.replace("_", " "),
            engine_kind=draft.kind,
        ),
    )
    partner = await ctx.session.get(EntityRow, draft.partner_id) if draft.partner_id is not None else None
    scope = current_scope()
    footprint = sorted({region for region in [await region_of(ctx.session, atlas, where.id), *draft.footprint] if region is not None})
    written = await record(
        ctx,
        f"event.{draft.kind.value}",
        roles={
            IncidentRole.SUBJECT: event.id,
            IncidentRole.PLACE: where.id,
            IncidentRole.ACTOR: partner.id if partner is not None else None,
            IncidentRole.AUTHORITY: scope.actor_node_id if scope is not None else None,
        },
        facts={"severity": clamp_int(draft.severity, 0, PERCENT), "regions": len(footprint)},
        steps=(StepDraft(StepAction.BEGIN, target=event.id),),
        place=where.id,
        world_id=where.world_id,
    )
    profile = await open_profile(ctx, event, incident_id=written.incident_id)
    if draft.start_year is not None:
        profile.start_year = max(0, draft.start_year)
    profile.start_season = await check_season(ctx, event.world_id, draft.start_season) if draft.start_season is not None else profile.start_season
    for region_id in {await region_of(ctx.session, atlas, where.id), *draft.footprint}:
        if region_id is not None:
            await require_region(ctx, region_id)
            await add_footprint(ctx.session, event.id, region_id, ctx.epoch)
    await onset(ctx, event, where, atlas, partner)
    if draft.phase is not EventPhase.ONSET:
        await turn(ctx, event, profile, draft.phase, atlas)
    hold(profile, "phase", draft.hold_phase)
    await ctx.session.flush()
    return event, profile


async def edit_event(ctx: TickContext, event_id: int, values: dict[str, int | str | None], *, lock: bool = True) -> EventProfileRow:
    event, profile = await require_event(ctx, event_id)
    for field, value in values.items():
        if field == "name":
            if not isinstance(value, str) or not value.strip():
                raise ValidationFailedError("An event needs a name.")
            event.name = value.strip()
        elif field == "severity":
            if not isinstance(value, int):
                raise ValidationFailedError("Severity takes a whole number.")
            set_stats(event, severity=clamp_int(value, 0, PERCENT))
        elif field in ("start_year", "end_year"):
            if value is not None and not isinstance(value, int):
                raise ValidationFailedError("Years are whole numbers.")
            setattr(profile, field, max(0, value) if isinstance(value, int) else None)
            hold(profile, field, lock and value is not None)
        elif field in ("start_season", "end_season"):
            position = value if isinstance(value, int) else None
            setattr(profile, field, await check_season(ctx, profile.world_id, position))
            hold(profile, field, lock and position is not None)
        else:
            raise ValidationFailedError(f"{field.replace('_', ' ')} cannot be set by hand.")
    if profile.end_year is not None and profile.start_year is not None and profile.end_year < profile.start_year:
        raise ValidationFailedError("An event cannot end before it begins.")
    await ctx.session.flush()
    return profile


async def set_phase(ctx: TickContext, event_id: int, phase: EventPhase, *, held: bool) -> EventProfileRow:
    event, profile = await require_event(ctx, event_id)
    if profile.end_epoch is not None:
        profile.end_epoch = profile.end_year = profile.end_season = None
    if phase is not profile.phase:
        await turn(ctx, event, profile, phase, await RegionAtlas.load(ctx.session))
    hold(profile, "phase", held)
    await ctx.session.flush()
    return profile


async def release(ctx: TickContext, event_id: int, field: str) -> EventProfileRow:
    _, profile = await require_event(ctx, event_id)
    if field not in PROFILE_FIELDS or field not in profile.locked:
        raise ValidationFailedError(f"The event's {field.replace('_', ' ')} is not held.")
    hold(profile, field, False)
    await ctx.session.flush()
    return profile


async def set_footprint(ctx: TickContext, event_id: int, region_id: int, *, present: bool) -> list[int]:
    await require_event(ctx, event_id)
    await require_region(ctx, region_id)
    if present:
        await add_footprint(ctx.session, event_id, region_id, ctx.epoch)
    else:
        row = await ctx.session.get(EventFootprintRow, (event_id, region_id))
        if row is not None:
            await ctx.session.delete(row)
    await ctx.session.flush()
    return list(await ctx.session.scalars(select(EventFootprintRow.region_entity_id).where(EventFootprintRow.event_entity_id == event_id)))


@dataclass(frozen=True)
class CohortToll:
    community_id: int
    age_band: AgeBand
    sex: Sex
    social_class: SocialClass
    phase: EventPhase
    count: int


async def set_casualties(ctx: TickContext, event_id: int, toll: CohortToll) -> int:
    await require_event(ctx, event_id)
    community = await ctx.session.get(EntityRow, toll.community_id)
    if community is None:
        raise NotFoundError("No such community.")
    key = (event_id, toll.community_id, toll.age_band, toll.sex, toll.social_class, toll.phase)
    row = await ctx.session.get(EventCasualtyRow, key)
    if toll.count <= 0:
        if row is not None:
            await ctx.session.delete(row)
    elif row is None:
        ctx.session.add(
            EventCasualtyRow(
                event_entity_id=event_id,
                community_entity_id=toll.community_id,
                age_band=toll.age_band,
                sex=toll.sex,
                social_class=toll.social_class,
                phase=toll.phase,
                count=toll.count,
            )
        )
    else:
        row.count = toll.count
    await ctx.session.flush()
    return max(0, toll.count)


async def end_event(ctx: TickContext, event_id: int) -> EventProfileRow:
    event, profile = await require_event(ctx, event_id)
    if profile.phase is not EventPhase.AFTERMATH:
        await turn(ctx, event, profile, EventPhase.AFTERMATH, await RegionAtlas.load(ctx.session))
    hold(profile, "phase", False)
    await close_profile(ctx, profile)
    await ctx.session.flush()
    return profile


async def set_land(ctx: TickContext, region_id: int, values: dict[str, int | bool | str | None], *, lock: bool) -> RegionGeomorphRow:
    region = await require_region(ctx, region_id)
    shape = await shape_of(ctx.session, region.id, region.world_id)
    for field, value in values.items():
        if field not in SHAPE_FIELDS:
            raise ValidationFailedError(f"{field.replace('_', ' ')} cannot be set by hand.")
        if field in ("desertification", "volcanic_pressure"):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValidationFailedError(f"{field.replace('_', ' ')} takes a whole number.")
            setattr(shape, field, clamp_int(value, 0, PERCENT))
        elif field in ("desertified", "volcanic"):
            if not isinstance(value, bool):
                raise ValidationFailedError(f"{field.replace('_', ' ')} is yes or no.")
            setattr(shape, field, value)
            if field == "desertified":
                shape.desert_since_epoch = ctx.epoch if value else None
        hold(shape, field, lock)
    ground = await ctx.session.get(RegionEnvironmentRow, region.id)
    if ground is not None and "desertified" in values:
        desert_terrain(ground, shape)
    await ctx.session.flush()
    return shape


async def release_land(ctx: TickContext, region_id: int, field: str) -> RegionGeomorphRow:
    region = await require_region(ctx, region_id)
    shape = await shape_of(ctx.session, region.id, region.world_id)
    if field not in shape.locked:
        raise ValidationFailedError(f"{region.name}'s {field.replace('_', ' ')} is not held.")
    hold(shape, field, False)
    await ctx.session.flush()
    return shape
