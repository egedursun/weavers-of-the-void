from pydantic import Field
from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.records import IncidentStepRow
from aerona.db.tables.tellings import IncidentNameRow, RumourDistortionRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import RumourDistortion, StepAction, StepOutcome
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

KEY_PATTERN = r"^[a-z][a-z0-9_]*$"
NAME_MAX = 200
DISTORTION_HOLDS = ("distortion", "target", "told")


class DistortionValues(Command):
    distortion: RumourDistortion | None = None
    role: IncidentRole | None = None
    fact_key: str | None = Field(default=None, pattern=KEY_PATTERN, max_length=80)
    step_id: int | None = None
    told_node_id: int | None = None
    told_number: float | None = None
    told_enum_value: str | None = Field(default=None, max_length=80)
    told_year: int | None = Field(default=None, ge=0)
    told_incident_id: int | None = None
    told_action: StepAction | None = None
    told_outcome: StepOutcome | None = None


class AddDistortion(DistortionValues):
    rumour_id: int


class EditDistortion(DistortionValues):
    rumour_distortion_id: int
    hold: list[str] = Field(default_factory=list)


class DistortionRef(Command):
    rumour_distortion_id: int


class SetName(Command):
    incident_id: int
    name: str = Field(min_length=1, max_length=NAME_MAX)
    language_entity_id: int | None = None
    hold: bool = True


class NameRef(Command):
    incident_id: int


async def rumour_of(scope: PlayerScope, rumour_id: int) -> RumourRow:
    rumour = await scope.session.get(RumourRow, rumour_id)
    if rumour is None:
        raise NotFoundError("No such rumour.")
    return rumour


async def distortion_of(scope: PlayerScope, row_id: int) -> RumourDistortionRow:
    row = await scope.session.get(RumourDistortionRow, row_id)
    if row is None:
        raise NotFoundError("No such change to a telling.")
    return row


async def checked(scope: PlayerScope, rumour: RumourRow, values: DistortionValues) -> None:
    if values.step_id is not None:
        step = await scope.session.get(IncidentStepRow, values.step_id)
        if step is None or step.incident_id != rumour.incident_id:
            raise ValidationFailedError("That step is not a step of the happening this rumour tells.")
    if values.told_node_id is not None and await scope.session.get(NodeRow, values.told_node_id) is None:
        raise NotFoundError("No such record to tell in its place.")
    if values.told_incident_id is not None and await scope.session.get(IncidentRow, values.told_incident_id) is None:
        raise NotFoundError("No such happening to tell as its cause.")


def apply(row: RumourDistortionRow, values: DistortionValues) -> None:
    for field in (
        "role",
        "fact_key",
        "step_id",
        "told_node_id",
        "told_number",
        "told_enum_value",
        "told_year",
        "told_incident_id",
        "told_action",
        "told_outcome",
    ):
        given = getattr(values, field)
        if given is not None:
            setattr(row, field, given)


@player_action("rumour_distortion:create", ActionKind.OTHER)
async def add_distortion(scope: PlayerScope, command: AddDistortion) -> Effect:
    rumour = await rumour_of(scope, command.rumour_id)
    if command.distortion is None:
        raise ValidationFailedError("Say how the telling is changed.")
    await checked(scope, rumour, command)
    last = await scope.session.scalar(
        select(RumourDistortionRow.position).where(RumourDistortionRow.rumour_id == rumour.id).order_by(RumourDistortionRow.position.desc()).limit(1)
    )
    row = RumourDistortionRow(
        rumour_id=rumour.id, position=last + 1 if last is not None else 0, distortion=command.distortion, epoch=await scope.epoch(), locked=[]
    )
    apply(row, command)
    scope.session.add(row)
    await scope.session.flush()
    return Effect("The rumour is now told with that change.")


@player_action("rumour_distortion:edit", ActionKind.OTHER)
async def edit_distortion(scope: PlayerScope, command: EditDistortion) -> Effect:
    row = await distortion_of(scope, command.rumour_distortion_id)
    unknown = [name for name in command.hold if name not in DISTORTION_HOLDS]
    if unknown:
        raise ValidationFailedError(f"A change to a telling has no part named {', '.join(unknown)}.")
    await checked(scope, await rumour_of(scope, row.rumour_id), command)
    if command.distortion is not None:
        row.distortion = command.distortion
    apply(row, command)
    row.locked = sorted({*row.locked, *command.hold})
    return Effect("The change to the telling was rewritten.")


@player_action("rumour_distortion:delete", ActionKind.OTHER)
async def delete_distortion(scope: PlayerScope, command: DistortionRef) -> Effect:
    row = await distortion_of(scope, command.rumour_distortion_id)
    await scope.session.delete(row)
    return Effect("The rumour no longer carries that change.")


@player_action("incident_name:set", ActionKind.OTHER)
async def set_name(scope: PlayerScope, command: SetName) -> Effect:
    if await scope.session.get(IncidentRow, command.incident_id) is None:
        raise NotFoundError("No such happening.")
    language = command.language_entity_id
    if language is not None and await scope.session.get(EntityRow, language) is None:
        raise NotFoundError("No such language.")
    row = await scope.session.get(IncidentNameRow, command.incident_id)
    if row is None:
        row = IncidentNameRow(incident_id=command.incident_id, name=command.name.strip(), language_entity_id=language, epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    else:
        row.name, row.language_entity_id, row.epoch = command.name.strip(), language, await scope.epoch()
    row.locked = ["name"] if command.hold else []
    await scope.session.flush()
    return Effect(f"The happening is called {row.name}.")


@player_action("incident_name:delete", ActionKind.OTHER)
async def delete_name(scope: PlayerScope, command: NameRef) -> Effect:
    row = await scope.session.get(IncidentNameRow, command.incident_id)
    if row is None:
        raise NotFoundError("That happening has no name.")
    await scope.session.delete(row)
    return Effect("The happening is no longer called by a name.")
