from typing import Any

from pydantic import Field
from sqlalchemy import JSON
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapper

from aerona.constants.control import BOOKKEEPING_TABLES
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.profile_guard import LOCK_COLUMN, NODE_TABLES, held_columns, owned_shape, profile_key, profile_mapper
from aerona.domain.enums.action import ActionKind
from aerona.services.player.profiles import NAME_PATTERN, ScalarValue, coerce, column_kind, pin_profile, scalar
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

JSON_KIND = "json"
JsonValue = ScalarValue | list[Any] | dict[str, Any]


class RowTarget(Command):
    table: str = Field(pattern=NAME_PATTERN)
    key: dict[str, ScalarValue]


class EditRow(RowTarget):
    values: dict[str, JsonValue] = Field(default_factory=dict)
    hold: bool = False
    release: list[str] = Field(default_factory=list)


class CreateRow(Command):
    table: str = Field(pattern=NAME_PATTERN)
    values: dict[str, JsonValue]


def controllable(table: str) -> Mapper[Any]:
    mapper = profile_mapper(table)
    if mapper is None or table in NODE_TABLES or table in BOOKKEEPING_TABLES or owned_shape(mapper) is None:
        raise NotFoundError(f"{table.replace('_', ' ')} is not a record the god can shape row by row.")
    return mapper


def editable_columns(mapper: Mapper[Any]) -> list[str]:
    keys = {mapper.get_property_by_column(column).key for column in mapper.primary_key}
    return [attribute.key for attribute in mapper.column_attrs if attribute.key not in keys and attribute.key != LOCK_COLUMN]


def is_json(mapper: Mapper[Any], column: str) -> bool:
    return isinstance(mapper.columns[column].type, JSON)


def value_for(mapper: Mapper[Any], column: str, value: JsonValue) -> Any:
    if column not in mapper.columns:
        raise ValidationFailedError(f"{mapper.class_.__tablename__.replace('_', ' ')} has no {column.replace('_', ' ')}.")
    if is_json(mapper, column):
        return value
    if isinstance(value, list | dict):
        raise ValidationFailedError(f"{column.replace('_', ' ').capitalize()} takes a single value.")
    if column_kind(mapper, column) is None:
        raise ValidationFailedError(f"{column.replace('_', ' ').capitalize()} cannot be set by hand.")
    return coerce(mapper, column, value)


async def row_of(scope: PlayerScope, mapper: Mapper[Any], key: dict[str, ScalarValue]) -> Any:
    names = [mapper.get_property_by_column(column).key for column in mapper.primary_key]
    if set(names) != set(key):
        raise ValidationFailedError(f"Name the row by {', '.join(names)}.")
    identity = tuple(coerce(mapper, name, key[name]) for name in names)
    row = await scope.session.get(mapper.class_, identity if len(identity) > 1 else identity[0])
    if row is None:
        raise NotFoundError("No such row.")
    return row


def label(mapper: Mapper[Any]) -> str:
    return str(mapper.class_.__tablename__).replace("_", " ")


async def flushed(scope: PlayerScope, what: str) -> None:
    try:
        async with scope.session.begin_nested():
            await scope.session.flush()
    except IntegrityError as error:
        raise ValidationFailedError(f"The {what} breaks what the world requires of it.") from error


def owner_of(mapper: Mapper[Any], row: Any) -> int | None:
    shape = owned_shape(mapper)
    if shape is None:
        return None
    return next((value for key in shape.owners if isinstance(value := getattr(row, key), int)), None)


@player_action("record_row:edit", ActionKind.EDIT_RECORD)
async def edit_row(scope: PlayerScope, command: EditRow) -> Effect:
    mapper = controllable(command.table)
    row = await row_of(scope, mapper, command.key)
    allowed = set(editable_columns(mapper))
    unknown = sorted(set(command.values) - allowed)
    if unknown:
        raise ValidationFailedError(f"These cannot be changed here: {', '.join(unknown)}.")
    for column, value in command.values.items():
        setattr(row, column, value_for(mapper, column, value))
    owner = owner_of(mapper, row)
    if command.release and LOCK_COLUMN in mapper.columns:
        setattr(row, LOCK_COLUMN, sorted(held_columns(row) - set(command.release)))
    if command.hold:
        if LOCK_COLUMN in mapper.columns:
            setattr(row, LOCK_COLUMN, sorted(held_columns(row) | set(command.values)))
        elif owner is not None:
            for column in command.values:
                await pin_profile(scope, owner, profile_key(str(mapper.class_.__tablename__), column))
    await flushed(scope, label(mapper))
    held = " and held" if command.hold else ""
    freed = ", and let follow the world again" if command.release else ""
    return Effect(f"A row of {label(mapper)} was reshaped{held}{freed}.", target_node_id=owner)


@player_action("record_row:delete", ActionKind.EDIT_RECORD)
async def delete_row(scope: PlayerScope, command: RowTarget) -> Effect:
    mapper = controllable(command.table)
    row = await row_of(scope, mapper, command.key)
    owner = owner_of(mapper, row)
    await scope.session.delete(row)
    await flushed(scope, label(mapper))
    return Effect(f"A row of {label(mapper)} was unmade.", target_node_id=owner)


@player_action("record_row:create", ActionKind.EDIT_RECORD)
async def create_row(scope: PlayerScope, command: CreateRow) -> Effect:
    mapper = controllable(command.table)
    values = {column: value_for(mapper, column, value) for column, value in command.values.items()}
    shape = owned_shape(mapper)
    if shape is not None and not any(isinstance(values.get(key), int) for key in shape.owners):
        raise ValidationFailedError(f"Name whom the {label(mapper)} belongs to: {', '.join(shape.owners)}.")
    if LOCK_COLUMN in mapper.columns and LOCK_COLUMN not in values:
        values[LOCK_COLUMN] = []
    row = mapper.class_(**values)
    scope.session.add(row)
    await flushed(scope, label(mapper))
    keys = [mapper.get_property_by_column(column).key for column in mapper.primary_key]
    return Effect(f"A new row of {label(mapper)} was made.", target_node_id=owner_of(mapper, row), values={key: scalar(getattr(row, key)) for key in keys})
