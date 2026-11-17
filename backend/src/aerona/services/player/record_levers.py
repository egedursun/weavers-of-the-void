import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import JSON, DateTime, Table, TypeDecorator, delete, select
from sqlalchemy.orm import Mapper

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, spoken
from aerona.db.base import Base
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, FactValue, InstrumentKind, StepAction, StepLocus, StepOutcome, StepState, WitnessMode
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

KEY_PATTERN = r"^[a-z][a-z0-9_]*$"
INCIDENT_HOLDS = ("text", "roles", "facts", "steps", "witnesses", "moment", "place")


class FactValues(BaseModel):
    node_id: int | None = None
    number: float | None = None
    unit: FactUnit | None = None
    enum_name: str | None = Field(default=None, max_length=80)
    enum_value: str | None = Field(default=None, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def one_value(self) -> "FactValues":
        given = [self.node_id is not None, self.number is not None, self.enum_value is not None, self.name is not None]
        if sum(given) != 1:
            raise ValueError("A fact holds exactly one value: a record, a number, an enum value or a name.")
        if self.unit is not None and self.number is None:
            raise ValueError("Only a number carries a unit.")
        if (self.enum_name is None) != (self.enum_value is None):
            raise ValueError("An enum value needs the name of its enum.")
        return self


class AddFact(Command, FactValues):
    incident_id: int
    key: str = Field(pattern=KEY_PATTERN, max_length=80)
    position: int = Field(default=0, ge=0, le=500)


class EditFact(Command, FactValues):
    incident_fact_id: int
    position: int | None = Field(default=None, ge=0, le=500)


class FactRef(Command):
    incident_fact_id: int


class StateEntry(BaseModel):
    node_id: int
    state: StepState


class StepValues(BaseModel):
    round: int | None = Field(default=None, ge=0, le=500)
    parent_step_id: int | None = None
    year: int | None = None
    season: int | None = Field(default=None, ge=0, le=100)
    day: int | None = Field(default=None, ge=0, le=1000)
    hour: int | None = Field(default=None, ge=0, le=100)
    actor_node_id: int | None = None
    target_node_id: int | None = None
    instrument_kind: InstrumentKind = InstrumentKind.NONE
    instrument_node_id: int | None = None
    instrument_key: str | None = Field(default=None, max_length=80)
    locus_kind: StepLocus = StepLocus.NONE
    locus_key: str | None = Field(default=None, max_length=80)
    locus_node_id: int | None = None
    damage_type: DamageType | None = None
    amount: float | None = None
    unit: FactUnit | None = None
    outcome: StepOutcome | None = None
    states: list[StateEntry] = Field(default_factory=list, max_length=40)


class AddStep(Command, StepValues):
    incident_id: int
    step_action: StepAction
    position: int | None = Field(default=None, ge=0, le=5000)


class EditStep(Command, StepValues):
    incident_step_id: int
    step_action: StepAction | None = None


class StepRef(Command):
    incident_step_id: int


class WitnessValues(BaseModel):
    witness_mode: WitnessMode = WitnessMode.SAW
    fidelity: int = Field(default=PERCENT_MAX, ge=0, le=PERCENT_MAX)


class AddWitness(Command, WitnessValues):
    incident_id: int
    node_id: int
    teller: bool = False


class EditWitness(Command):
    incident_id: int
    node_id: int
    teller: bool = False
    witness_mode: WitnessMode | None = None
    fidelity: int | None = Field(default=None, ge=0, le=PERCENT_MAX)


class WitnessRef(Command):
    incident_id: int
    node_id: int
    teller: bool = False


class HoldIncident(Command):
    incident_id: int
    fields: list[str] = Field(default_factory=lambda: list(INCIDENT_HOLDS), min_length=1)
    hold: bool = True


class ChangeRef(Command):
    state_change_id: int


async def incident_of(scope: PlayerScope, incident_id: int) -> IncidentRow:
    row = await scope.session.get(IncidentRow, incident_id)
    if row is None:
        raise NotFoundError("No such incident.")
    return row


def kind_of(incident: IncidentRow) -> IncidentKindSpec | None:
    return INCIDENT_KINDS.get(incident.kind)


async def node_exists(scope: PlayerScope, node_id: int | None, what: str) -> None:
    if node_id is not None and await scope.session.get(NodeRow, node_id) is None:
        raise NotFoundError(f"No record can be the {what}.")


def checked_fact(spec: IncidentKindSpec | None, key: str, values: FactValues) -> None:
    if spec is None or spec.draft:
        return
    declared = spec.fact(key)
    if declared is None and spec.open_facts:
        return
    if declared is None:
        raise ValidationFailedError(f"A happening of the kind {spec.key} keeps no fact named {key}.")
    given = (
        FactValue.NODE
        if values.node_id is not None
        else FactValue.NUMBER
        if values.number is not None
        else FactValue.ENUM
        if values.enum_value is not None
        else FactValue.NAME
    )
    if given is not declared.value:
        raise ValidationFailedError(f"The fact {key} holds {an(spoken(declared.value))}, not {an(spoken(given))}.")
    if declared.unit is not None and values.unit is not None and values.unit is not declared.unit:
        raise ValidationFailedError(f"The fact {key} is counted in {spoken(declared.unit)}.")
    if declared.enum is not None and values.enum_value is not None:
        if values.enum_name != declared.enum.__name__:
            raise ValidationFailedError(f"The fact {key} holds a value of {declared.enum.__name__}.")
        if values.enum_value not in {member.value for member in declared.enum}:
            raise ValidationFailedError(f"{values.enum_value} is no value of {declared.enum.__name__}.")


def put_fact(row: IncidentFactRow, values: FactValues, unit: FactUnit | None) -> None:
    row.node_id = values.node_id
    row.number = values.number
    row.unit = values.unit if values.unit is not None else unit if values.number is not None else None
    row.enum_name = values.enum_name
    row.enum_value = values.enum_value
    row.name = values.name


@player_action("incident_fact:create", ActionKind.OTHER)
async def add_fact(scope: PlayerScope, command: AddFact) -> Effect:
    incident = await incident_of(scope, command.incident_id)
    spec = kind_of(incident)
    checked_fact(spec, command.key, command)
    await node_exists(scope, command.node_id, "value of this fact")
    declared = spec.fact(command.key) if spec is not None else None
    row = IncidentFactRow(incident_id=incident.id, key=command.key, position=command.position)
    put_fact(row, command, declared.unit if declared is not None else None)
    scope.session.add(row)
    await scope.session.flush()
    return Effect(f"The fact {command.key} was set down in the account of the happening.", created_ids=(row.id,))


async def fact_of(scope: PlayerScope, fact_id: int) -> IncidentFactRow:
    row = await scope.session.get(IncidentFactRow, fact_id)
    if row is None:
        raise NotFoundError("No such fact.")
    return row


@player_action("incident_fact:edit", ActionKind.OTHER)
async def edit_fact(scope: PlayerScope, command: EditFact) -> Effect:
    row = await fact_of(scope, command.incident_fact_id)
    incident = await incident_of(scope, row.incident_id)
    spec = kind_of(incident)
    checked_fact(spec, row.key, command)
    await node_exists(scope, command.node_id, "value of this fact")
    declared = spec.fact(row.key) if spec is not None else None
    put_fact(row, command, declared.unit if declared is not None else None)
    if command.position is not None:
        row.position = command.position
    return Effect(f"The fact {row.key} was rewritten.")


@player_action("incident_fact:delete", ActionKind.OTHER)
async def delete_fact(scope: PlayerScope, command: FactRef) -> Effect:
    row = await fact_of(scope, command.incident_fact_id)
    incident = await incident_of(scope, row.incident_id)
    spec = kind_of(incident)
    declared = spec.fact(row.key) if spec is not None and not spec.draft else None
    if declared is not None and declared.required and not declared.many:
        raise ValidationFailedError(f"A happening of the kind {incident.kind} cannot be told without its {row.key}; rewrite it instead.")
    await scope.session.delete(row)
    return Effect(f"The fact {row.key} was struck from the account.")


async def step_of(scope: PlayerScope, step_id: int) -> IncidentStepRow:
    row = await scope.session.get(IncidentStepRow, step_id)
    if row is None:
        raise NotFoundError("No such step.")
    return row


async def checked_step(scope: PlayerScope, incident: IncidentRow, action: StepAction, values: StepValues, own_id: int | None) -> None:
    spec = kind_of(incident)
    if spec is not None and not spec.draft and spec.steps and action not in spec.steps:
        raise ValidationFailedError(f"A happening of the kind {incident.kind} has no step of the kind {spoken(action)}.")
    for node_id, what in (
        (values.actor_node_id, "one who acts"),
        (values.target_node_id, "one acted on"),
        (values.instrument_node_id, "instrument"),
        (values.locus_node_id, "place of the step"),
    ):
        await node_exists(scope, node_id, what)
    for entry in values.states:
        await node_exists(scope, entry.node_id, "one whose state changed")
    if values.unit is not None and values.amount is None:
        raise ValidationFailedError("Only an amount carries a unit.")
    if values.parent_step_id is not None:
        parent = await step_of(scope, values.parent_step_id)
        if parent.incident_id != incident.id:
            raise ValidationFailedError("A step can only nest inside a step of the same happening.")
        if own_id is not None and await descends_from(scope, parent, own_id):
            raise ValidationFailedError("A step cannot nest inside itself.")


async def descends_from(scope: PlayerScope, step: IncidentStepRow, ancestor_id: int) -> bool:
    current: IncidentStepRow | None = step
    seen: set[int] = set()
    while current is not None and current.id not in seen:
        if current.id == ancestor_id:
            return True
        seen.add(current.id)
        current = await scope.session.get(IncidentStepRow, current.parent_step_id) if current.parent_step_id is not None else None
    return False


def moment_key(row: IncidentStepRow) -> tuple[int, int, int, int] | None:
    if row.year is None:
        return None
    return (row.year, row.season or 0, row.day or 0, row.hour or 0)


async def checked_order(scope: PlayerScope, incident_id: int) -> None:
    rows = list(
        await scope.session.scalars(
            select(IncidentStepRow).where(IncidentStepRow.incident_id == incident_id).order_by(IncidentStepRow.position, IncidentStepRow.id)
        )
    )
    last: tuple[int, int, int, int] | None = None
    for row in rows:
        here = moment_key(row)
        if here is None:
            continue
        if last is not None and here < last:
            raise ValidationFailedError("A step cannot come before the step told ahead of it; move it or change its moment.")
        last = here


def put_step(row: IncidentStepRow, values: StepValues) -> None:
    for name in (
        "round",
        "parent_step_id",
        "year",
        "season",
        "day",
        "hour",
        "actor_node_id",
        "target_node_id",
        "instrument_kind",
        "instrument_node_id",
        "instrument_key",
        "locus_kind",
        "locus_key",
        "locus_node_id",
        "damage_type",
        "amount",
        "unit",
        "outcome",
    ):
        setattr(row, name, getattr(values, name))


async def put_states(scope: PlayerScope, step: IncidentStepRow, states: list[StateEntry]) -> None:
    await scope.session.execute(delete(IncidentStepStateRow).where(IncidentStepStateRow.step_id == step.id))
    seen = {(entry.node_id, entry.state) for entry in states}
    scope.session.add_all(
        IncidentStepStateRow(step_id=step.id, node_id=node_id, state=state) for node_id, state in sorted(seen, key=lambda item: (item[0], item[1].value))
    )
    await scope.session.flush()


@player_action("incident_step:create", ActionKind.OTHER)
async def add_step(scope: PlayerScope, command: AddStep) -> Effect:
    incident = await incident_of(scope, command.incident_id)
    await checked_step(scope, incident, command.step_action, command, None)
    last = await scope.session.scalar(
        select(IncidentStepRow.position).where(IncidentStepRow.incident_id == incident.id).order_by(IncidentStepRow.position.desc()).limit(1)
    )
    row = IncidentStepRow(
        incident_id=incident.id,
        position=command.position if command.position is not None else (last + 1 if last is not None else 0),
        action=command.step_action,
    )
    put_step(row, command)
    scope.session.add(row)
    await scope.session.flush()
    await put_states(scope, row, command.states)
    await checked_order(scope, incident.id)
    return Effect(f"A step ({spoken(command.step_action)}) was added to how the happening unfolded.", created_ids=(row.id,))


@player_action("incident_step:edit", ActionKind.OTHER)
async def edit_step(scope: PlayerScope, command: EditStep) -> Effect:
    row = await step_of(scope, command.incident_step_id)
    incident = await incident_of(scope, row.incident_id)
    action = command.step_action or row.action
    await checked_step(scope, incident, action, command, row.id)
    row.action = action
    put_step(row, command)
    await scope.session.flush()
    await put_states(scope, row, command.states)
    await checked_order(scope, incident.id)
    return Effect("The step was rewritten.")


@player_action("incident_step:delete", ActionKind.OTHER)
async def delete_step(scope: PlayerScope, command: StepRef) -> Effect:
    row = await step_of(scope, command.incident_step_id)
    for child in list(await scope.session.scalars(select(IncidentStepRow).where(IncidentStepRow.parent_step_id == row.id))):
        child.parent_step_id = row.parent_step_id
    await scope.session.flush()
    await scope.session.delete(row)
    return Effect("The step was struck from how the happening unfolded; what nested inside it moved up a level.")


def telling_role(teller: bool) -> IncidentRole:
    return IncidentRole.TELLER if teller else IncidentRole.WITNESS


async def witness_of(scope: PlayerScope, incident_id: int, node_id: int, teller: bool) -> IncidentParticipantRow:
    row = await scope.session.get(IncidentParticipantRow, (incident_id, node_id, telling_role(teller)))
    if row is None:
        raise NotFoundError(
            "That record is not set down as a witness of this happening." if not teller else "That record is not set down as a teller of this happening."
        )
    return row


@player_action("incident_witness:create", ActionKind.OTHER)
async def add_witness(scope: PlayerScope, command: AddWitness) -> Effect:
    incident = await incident_of(scope, command.incident_id)
    await node_exists(scope, command.node_id, "witness")
    role = telling_role(command.teller)
    if await scope.session.get(IncidentParticipantRow, (incident.id, command.node_id, role)) is not None:
        raise ValidationFailedError("That record already holds this place in the happening.")
    last = await scope.session.scalar(
        select(IncidentParticipantRow.position)
        .where(IncidentParticipantRow.incident_id == incident.id)
        .order_by(IncidentParticipantRow.position.desc())
        .limit(1)
    )
    scope.session.add(
        IncidentParticipantRow(
            incident_id=incident.id,
            node_id=command.node_id,
            role=role,
            position=last + 1 if last is not None else 0,
            witness_mode=command.witness_mode,
            fidelity=command.fidelity,
        )
    )
    await scope.session.flush()
    return Effect("A teller of the happening was set down." if command.teller else "A witness of the happening was set down.")


@player_action("incident_witness:edit", ActionKind.OTHER)
async def edit_witness(scope: PlayerScope, command: EditWitness) -> Effect:
    row = await witness_of(scope, command.incident_id, command.node_id, command.teller)
    if command.witness_mode is not None:
        row.witness_mode = command.witness_mode
    if command.fidelity is not None:
        row.fidelity = command.fidelity
    return Effect("How the happening was seen and told was rewritten.")


@player_action("incident_witness:delete", ActionKind.OTHER)
async def delete_witness(scope: PlayerScope, command: WitnessRef) -> Effect:
    row = await witness_of(scope, command.incident_id, command.node_id, command.teller)
    await scope.session.delete(row)
    return Effect("The teller was struck from the happening." if command.teller else "The witness was struck from the happening.")


@player_action("incident:hold", ActionKind.OTHER)
async def hold_incident(scope: PlayerScope, command: HoldIncident) -> Effect:
    incident = await incident_of(scope, command.incident_id)
    unknown = [name for name in command.fields if name not in INCIDENT_HOLDS]
    if unknown:
        raise ValidationFailedError(f"A happening has no part named {', '.join(unknown)}.")
    kept = [name for name in incident.locked or [] if name not in command.fields]
    incident.locked = sorted({*kept, *command.fields}) if command.hold else kept
    return Effect(f"{'Held' if command.hold else 'Released'}: {', '.join(command.fields)} of the happening.")


def table_of(name: str) -> tuple[Table, Mapper[Any]]:
    for mapper in Base.registry.mappers:
        if mapper.local_table is not None and getattr(mapper.local_table, "name", None) == name and isinstance(mapper.local_table, Table):
            return mapper.local_table, mapper
    raise NotFoundError(f"No table named {name} keeps records.")


def python_of(column: Any) -> type | None:
    try:
        found: type = column.type.python_type
    except NotImplementedError:
        return None
    return found


def column_value(table: Table, name: str, value: Any) -> Any:
    column = table.c[name]
    enum_class = getattr(column.type, "enum_class", None)
    if value is None or isinstance(column.type, JSON):
        return value
    if isinstance(enum_class, type) and issubclass(enum_class, Enum):
        return enum_class(value)
    python = python_of(column)
    stored = column.type.impl if isinstance(column.type, TypeDecorator) else column.type
    if isinstance(value, str) and (isinstance(stored, DateTime) or python is datetime):
        return datetime.fromisoformat(value)
    return int(value) if python is int and isinstance(value, float) else value


def before_value(table: Table, change: StateChangeRow) -> Any:
    if change.field is None:
        return None
    column = table.c[change.field]
    if change.before_node_id is not None:
        return change.before_node_id
    if change.before_number is not None:
        return column_value(table, change.field, change.before_number)
    if change.before_text is None:
        return None
    if isinstance(column.type, JSON):
        return json.loads(change.before_text)
    return column_value(table, change.field, change.before_text)


async def live_row(scope: PlayerScope, mapper: Mapper[Any], table: Table, key: dict[str, Any]) -> Any:
    identity = tuple(column_value(table, column.name, key.get(column.name)) for column in table.primary_key.columns)
    return await scope.session.get(mapper.class_, identity if len(identity) > 1 else identity[0])


def attribute_of(mapper: Mapper[Any], table: Table, name: str) -> str:
    return mapper.get_property_by_column(table.c[name]).key


async def change_of(scope: PlayerScope, change_id: int) -> StateChangeRow:
    row = await scope.session.get(StateChangeRow, change_id)
    if row is None:
        raise NotFoundError("No such change in the record of the world.")
    return row


@player_action("state_change:revert", ActionKind.OTHER)
async def revert_change(scope: PlayerScope, command: ChangeRef) -> Effect:
    change = await change_of(scope, command.state_change_id)
    table, mapper = table_of(change.table_name)
    key = json.loads(change.row_key)
    row = await live_row(scope, mapper, table, key)
    if change.operation is LedgerOperation.UPDATE:
        if row is None or change.field is None:
            raise ValidationFailedError("The record this change touched no longer exists; restore it first.")
        setattr(row, attribute_of(mapper, table, change.field), before_value(table, change))
        await scope.session.flush()
        return Effect(f"The {change.field} of the record was set back to what it was before; the reversal is itself kept in history.")
    if change.operation is LedgerOperation.INSERT:
        if row is None:
            raise ValidationFailedError("The record this change made is already gone.")
        await scope.session.delete(row)
        await scope.session.flush()
        return Effect("The record this change made was unmade; the reversal is itself kept in history.")
    if row is not None:
        raise ValidationFailedError("The record this change removed exists again.")
    if change.before_text is None:
        raise ValidationFailedError("The change kept no copy of the removed record.")
    values = json.loads(change.before_text)
    restored = mapper.class_(**{attribute_of(mapper, table, name): column_value(table, name, value) for name, value in values.items() if name in table.c})
    scope.session.add(restored)
    await scope.session.flush()
    return Effect("The removed record was restored as it was; the reversal is itself kept in history.")


@player_action("state_change:delete", ActionKind.OTHER)
async def delete_change(scope: PlayerScope, command: ChangeRef) -> Effect:
    change = await change_of(scope, command.state_change_id)
    await scope.session.delete(change)
    return Effect("The change was erased from the record of the world.")
