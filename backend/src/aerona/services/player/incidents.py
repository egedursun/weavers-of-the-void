from pydantic import BaseModel, Field
from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.base import Base
from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.modifier import IncidentRole
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

KIND_PATTERN = r"^[a-z][a-z0-9_.]*$"
PLAYER_KIND = "player.history"
INCIDENTS_TABLE = IncidentRow.__tablename__


class Participant(BaseModel):
    node_id: int
    role: IncidentRole = IncidentRole.SUBJECT


class CreateIncident(Command):
    text: str = Field(min_length=1, max_length=2000)
    kind: str = Field(default=PLAYER_KIND, pattern=KIND_PATTERN, max_length=80)
    epoch: int | None = Field(default=None, ge=1)
    year: int | None = None
    magnitude: int = Field(default=30, ge=0, le=PERCENT_MAX)
    place_entity_id: int | None = None
    cause_incident_id: int | None = None
    participants: list[Participant] = Field(default_factory=list, max_length=40)


class EditIncident(Command):
    incident_id: int
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    kind: str | None = Field(default=None, pattern=KIND_PATTERN, max_length=80)
    magnitude: int | None = Field(default=None, ge=0, le=PERCENT_MAX)
    year: int | None = None
    place_entity_id: int | None = None
    clear_place: bool = False


class SetIncidentRoles(Command):
    incident_id: int
    participants: list[Participant] = Field(max_length=40)


class LinkCause(Command):
    incident_id: int
    cause_incident_id: int


class IncidentRef(Command):
    incident_id: int


async def _incident(scope: PlayerScope, incident_id: int) -> IncidentRow:
    row = await scope.session.get(IncidentRow, incident_id)
    if row is None:
        raise NotFoundError("No such incident.")
    return row


async def _check_nodes(scope: PlayerScope, participants: list[Participant]) -> None:
    for item in participants:
        if await scope.session.get(NodeRow, item.node_id) is None:
            raise NotFoundError(f"No record has the id {item.node_id}.")
    seen = {(item.node_id, item.role) for item in participants}
    if len(seen) != len(participants):
        raise ValidationFailedError("A record can hold each role only once in an incident.")


async def _place(scope: PlayerScope, place_entity_id: int | None) -> int | None:
    if place_entity_id is None:
        return None
    if await scope.session.get(EntityRow, place_entity_id) is None:
        raise NotFoundError("No such place.")
    return place_entity_id


async def _check_cause(scope: PlayerScope, incident: IncidentRow, cause_id: int) -> IncidentRow:
    cause = await _incident(scope, cause_id)
    if cause.id == incident.id:
        raise ValidationFailedError("An incident cannot cause itself.")
    if cause.epoch > incident.epoch:
        raise ValidationFailedError("A cause cannot come after what it caused.")
    current: int | None = cause.cause_incident_id
    seen: set[int] = {cause.id}
    while current is not None and current not in seen:
        if current == incident.id:
            raise ValidationFailedError("That link would make the incident its own cause.")
        seen.add(current)
        parent = await scope.session.get(IncidentRow, current)
        current = parent.cause_incident_id if parent is not None else None
    return cause


async def _replace_participants(scope: PlayerScope, incident: IncidentRow, participants: list[Participant]) -> None:
    for row in list(await scope.session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident.id))):
        await scope.session.delete(row)
    await scope.session.flush()
    scope.session.add_all(
        IncidentParticipantRow(incident_id=incident.id, node_id=item.node_id, role=item.role, position=position) for position, item in enumerate(participants)
    )
    await scope.session.flush()


@player_action("incident:create", ActionKind.OTHER)
async def create_incident(scope: PlayerScope, command: CreateIncident) -> Effect:
    await _check_nodes(scope, command.participants)
    place = await _place(scope, command.place_entity_id)
    epoch = command.epoch or await scope.epoch()
    if epoch > await scope.epoch():
        raise ValidationFailedError("History cannot be written ahead of the present epoch.")
    if command.cause_incident_id is not None:
        cause = await _incident(scope, command.cause_incident_id)
        if cause.epoch > epoch:
            raise ValidationFailedError("A cause cannot come after what it caused.")
    entity_ids = [item.node_id for item in command.participants if await scope.session.get(EntityRow, item.node_id) is not None]
    draft = ChronicleDraft(
        epoch=epoch,
        kind=ChronicleKind.CREATOR_HAND,
        text=command.text,
        entity_ids=entity_ids,
        template_key=command.kind,
        cause_incident_id=command.cause_incident_id,
        place_entity_id=place,
        magnitude=command.magnitude,
        year=command.year,
        roles={item.node_id: item.role for item in command.participants},
    )
    write = await ChronicleRepository(scope.session).append(draft)
    incident = await _incident(scope, write.incident_id or 0)
    if command.cause_incident_id is None:
        incident.cause_incident_id = None
    incident.magnitude = command.magnitude
    await _replace_participants(scope, incident, command.participants)
    return Effect(f"A new incident was written into history: {write.row.text}", created_ids=(incident.id,))


@player_action("incident:edit", ActionKind.OTHER)
async def edit_incident(scope: PlayerScope, command: EditIncident) -> Effect:
    incident = await _incident(scope, command.incident_id)
    chronicle = await scope.session.get(ChronicleRow, incident.chronicle_id) if incident.chronicle_id is not None else None
    if command.text is not None:
        if chronicle is None:
            raise ValidationFailedError("This incident has no chronicle line to rewrite.")
        chronicle.text = " ".join(command.text.split())
    if command.kind is not None:
        incident.kind = command.kind
    if command.magnitude is not None:
        incident.magnitude = command.magnitude
    if command.year is not None:
        incident.year = command.year
        if chronicle is not None:
            chronicle.year = command.year
    if command.clear_place:
        incident.place_entity_id = None
    elif command.place_entity_id is not None:
        incident.place_entity_id = await _place(scope, command.place_entity_id)
    return Effect("The incident was rewritten.")


@player_action("incident:roles", ActionKind.OTHER)
async def set_incident_roles(scope: PlayerScope, command: SetIncidentRoles) -> Effect:
    incident = await _incident(scope, command.incident_id)
    await _check_nodes(scope, command.participants)
    await _replace_participants(scope, incident, command.participants)
    return Effect(f"The incident now names {several(len(command.participants), 'participant', 'participants')} with their roles.")


@player_action("incident:link_cause", ActionKind.OTHER)
async def link_cause(scope: PlayerScope, command: LinkCause) -> Effect:
    incident = await _incident(scope, command.incident_id)
    cause = await _check_cause(scope, incident, command.cause_incident_id)
    incident.cause_incident_id = cause.id
    span = f" across {several(incident.epoch - cause.epoch, 'epoch', 'epochs')}" if incident.epoch > cause.epoch else ""
    return Effect(f"The incident now follows from incident {cause.id}{span}.")


@player_action("incident:unlink_cause", ActionKind.OTHER)
async def unlink_cause(scope: PlayerScope, command: IncidentRef) -> Effect:
    incident = await _incident(scope, command.incident_id)
    if incident.cause_incident_id is None:
        raise ValidationFailedError("This incident has no recorded cause.")
    incident.cause_incident_id = None
    return Effect("The incident no longer follows from anything.")


def _incident_references() -> list[tuple[type[Base], str]]:
    found: list[tuple[type[Base], str]] = []
    for mapper in Base.registry.mappers:
        for column in mapper.columns:
            if any(key.column.table.name == INCIDENTS_TABLE for key in column.foreign_keys) and mapper.class_ is not IncidentParticipantRow:
                found.append((mapper.class_, column.key))
    return sorted(found, key=lambda item: (item[0].__name__, item[1]))


@player_action("incident:delete", ActionKind.OTHER)
async def delete_incident(scope: PlayerScope, command: IncidentRef) -> Effect:
    incident = await _incident(scope, command.incident_id)
    for model, column in _incident_references():
        attribute = getattr(model, column)
        for row in list(await scope.session.scalars(select(model).where(attribute == incident.id))):
            setattr(row, column, incident.cause_incident_id if model is IncidentRow and column == "cause_incident_id" else None)
    for row in list(await scope.session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident.id))):
        await scope.session.delete(row)
    chronicle = await scope.session.get(ChronicleRow, incident.chronicle_id) if incident.chronicle_id is not None else None
    await scope.session.flush()
    await scope.session.delete(incident)
    if chronicle is not None:
        chronicle.visible = False
    return Effect("The incident was struck from history; what it caused now follows from its own cause.")
