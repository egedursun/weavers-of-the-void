from typing import Literal

from pydantic import Field

from aerona.catalog.interventions import DISASTERS
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.demography import AgeBand, Sex
from aerona.domain.enums.entity import EngineKind
from aerona.domain.enums.happening import EventPhase, RiverShiftCause
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.society import SocialClass
from aerona.engine.environment.geomorph import shift_river
from aerona.engine.happenings import control
from aerona.engine.phases.disasters import send_disaster
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_MAX = 120
TEXT_MAX = 2000
VOLCANIC = (Disaster.ERUPTION, Disaster.VOLCANIC_QUAKE)
PHASE_WORDS = {EventPhase.ONSET: "beginning", EventPhase.PEAK: "height", EventPhase.AFTERMATH: "aftermath"}


class CreateEvent(Command):
    kind: EngineKind
    where_id: int
    name: str = Field(default="", max_length=NAME_MAX)
    description: str = Field(default="", max_length=TEXT_MAX)
    severity: int = Field(default=50, ge=0, le=100)
    phase: EventPhase = EventPhase.ONSET
    hold_phase: bool = False
    start_year: int | None = Field(default=None, ge=0)
    start_season: int | None = Field(default=None, ge=0)
    footprint: list[int] = Field(default_factory=list)
    partner_id: int | None = None


class EditEvent(Command):
    event_id: int
    values: dict[str, int | str | None] = Field(default_factory=dict)
    lock: bool = True


class EventPhaseCommand(Command):
    event_id: int
    phase: EventPhase
    hold: bool = True


class EventRelease(Command):
    event_id: int
    field: Literal["phase", "start_year", "start_season", "end_year", "end_season"] = "phase"


class EventFootprint(Command):
    event_id: int
    region_id: int
    present: bool = True


class EventCasualties(Command):
    event_id: int
    community_id: int
    age_band: AgeBand
    sex: Sex
    social_class: SocialClass
    phase: EventPhase = EventPhase.ONSET
    count: int = Field(ge=0)


class EventTarget(Command):
    event_id: int


class StirLand(Command):
    region_id: int
    disaster: Disaster = Disaster.ERUPTION
    severity: int | None = Field(default=None, ge=1, le=100)


class MoveRiver(Command):
    from_region_id: int
    to_region_id: int | None = None


class ShapeLand(Command):
    region_id: int
    desertification: int | None = Field(default=None, ge=0, le=100)
    desertified: bool | None = None
    volcanic: bool | None = None
    volcanic_pressure: int | None = Field(default=None, ge=0, le=100)
    hold: bool = True


class ReleaseLand(Command):
    region_id: int
    field: Literal["desertification", "desertified", "volcanic", "volcanic_pressure"]


@player_action("event:create", ActionKind.OTHER)
async def create_event(scope: PlayerScope, command: CreateEvent) -> Effect:
    draft = control.EventDraft(
        kind=command.kind,
        name=command.name,
        where_id=command.where_id,
        severity=command.severity,
        description=command.description,
        phase=command.phase,
        start_year=command.start_year,
        start_season=command.start_season,
        footprint=tuple(command.footprint),
        partner_id=command.partner_id,
        hold_phase=command.hold_phase,
    )
    event, _ = await control.create_event(await scope.context("event_create"), draft)
    return Effect(f"{event.name} came to pass.", event.id, created_ids=(event.id,))


@player_action("event:edit", ActionKind.EDIT_RECORD)
async def edit_event(scope: PlayerScope, command: EditEvent) -> Effect:
    profile = await control.edit_event(await scope.context("event_edit"), command.event_id, command.values, lock=command.lock)
    held = f"; held: {', '.join(item.replace('_', ' ') for item in profile.locked)}" if profile.locked else ""
    return Effect(f"The event's record now runs from {profile.start_year} to {profile.end_year or 'today'}{held}.", command.event_id)


@player_action("event:phase", ActionKind.OTHER)
async def set_event_phase(scope: PlayerScope, command: EventPhaseCommand) -> Effect:
    profile = await control.set_phase(await scope.context("event_phase"), command.event_id, command.phase, held=command.hold)
    held = " and held there" if command.hold else ""
    return Effect(f"The event is at its {PHASE_WORDS[profile.phase]}{held}.", command.event_id)


@player_action("event:release", ActionKind.OTHER)
async def release_event(scope: PlayerScope, command: EventRelease) -> Effect:
    await control.release(await scope.context("event_release"), command.event_id, command.field)
    return Effect(f"The event's {command.field.replace('_', ' ')} follows the world again.", command.event_id)


@player_action("event:footprint", ActionKind.OTHER)
async def set_event_footprint(scope: PlayerScope, command: EventFootprint) -> Effect:
    regions = await control.set_footprint(await scope.context("event_footprint"), command.event_id, command.region_id, present=command.present)
    return Effect(f"The event now reaches {several(len(regions), 'land', 'lands')}.", command.event_id)


@player_action("event:casualties", ActionKind.EDIT_RECORD)
async def set_event_casualties(scope: PlayerScope, command: EventCasualties) -> Effect:
    toll = control.CohortToll(command.community_id, command.age_band, command.sex, command.social_class, command.phase, command.count)
    count = await control.set_casualties(await scope.context("event_casualties"), command.event_id, toll)
    return Effect(f"The toll is set at {count} for that cohort.", command.event_id)


@player_action("event:end", ActionKind.OTHER)
async def end_event(scope: PlayerScope, command: EventTarget) -> Effect:
    profile = await control.end_event(await scope.context("event_end"), command.event_id)
    return Effect(f"The event is over (year {profile.end_year}).", command.event_id)


@player_action("land:stir", ActionKind.DISASTER)
async def stir_land(scope: PlayerScope, command: StirLand) -> Effect:
    if command.disaster not in VOLCANIC:
        raise ValidationFailedError("Only an eruption or a volcanic earthquake can be stirred here.")
    event = await send_disaster(await scope.context("land_stir"), command.region_id, command.disaster, command.severity)
    return Effect(f"{DISASTERS[command.disaster].label} struck: {event.name}.", command.region_id, created_ids=(event.id,))


@player_action("land:river", ActionKind.OTHER)
async def move_river(scope: PlayerScope, command: MoveRiver) -> Effect:
    shift = await shift_river(await scope.context("land_river"), command.from_region_id, command.to_region_id, RiverShiftCause.PLAYER)
    if shift is None:
        raise ValidationFailedError("The river cannot be moved there: it needs a flowing river, a free bed and a neighbouring land.")
    return Effect("The river found a new bed.", command.from_region_id, values={"to_region_id": shift.to_region_id})


@player_action("land:shape", ActionKind.OTHER)
async def shape_land(scope: PlayerScope, command: ShapeLand) -> Effect:
    values: dict[str, int | bool | str | None] = {
        key: value
        for key, value in (
            ("desertification", command.desertification),
            ("desertified", command.desertified),
            ("volcanic", command.volcanic),
            ("volcanic_pressure", command.volcanic_pressure),
        )
        if value is not None
    }
    if not values:
        raise ValidationFailedError("Choose something to change.")
    shape = await control.set_land(await scope.context("land_shape"), command.region_id, values, lock=command.hold)
    held = " and held" if command.hold else ""
    return Effect(f"The land is {shape.desertification}% desert, volcanic pressure {shape.volcanic_pressure}{held}.", command.region_id)


@player_action("land:release", ActionKind.OTHER)
async def release_land(scope: PlayerScope, command: ReleaseLand) -> Effect:
    await control.release_land(await scope.context("land_release"), command.region_id, command.field)
    return Effect(f"The land's {command.field.replace('_', ' ')} follows the world again.", command.region_id)
