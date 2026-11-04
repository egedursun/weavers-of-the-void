from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import Field
from sqlalchemy import Boolean, Float, Integer, String, delete, select
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.base import Base
from aerona.db.profile_guard import LOCK_COLUMN, ProfileShape, held_columns, profile_key, profile_mapper, shape_of_table, table_name
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_PATTERN = r"^[a-z][a-z0-9_]*$"
INTEGER_KIND = "integer"
NUMBER_KIND = "number"
FLAG_KIND = "flag"
CHOICE_KIND = "choice"
TEXT_KIND = "text"
ScalarValue = int | float | str | bool | None


@dataclass(frozen=True)
class ProfileColumn:
    name: str
    kind: str
    value: ScalarValue
    options: tuple[str, ...]
    nullable: bool
    held: bool
    pinned: bool


@dataclass(frozen=True)
class ProfileTable:
    table: str
    node_column: str
    lockable: bool
    columns: tuple[ProfileColumn, ...]


class SetProfileValue(Command):
    node_id: int
    table: str = Field(pattern=NAME_PATTERN)
    column: str = Field(pattern=NAME_PATTERN)
    value: ScalarValue
    hold: bool = True


class ReleaseProfileValue(Command):
    node_id: int
    table: str = Field(pattern=NAME_PATTERN)
    column: str = Field(pattern=NAME_PATTERN)


def column_kind(mapper: Mapper[Any], column: str) -> tuple[str, tuple[str, ...]] | None:
    sql_type = mapper.columns[column].type
    if isinstance(sql_type, SqlEnum):
        return CHOICE_KIND, tuple(str(item) for item in sql_type.enums)
    if isinstance(sql_type, Boolean):
        return FLAG_KIND, ()
    if isinstance(sql_type, Integer):
        return INTEGER_KIND, ()
    if isinstance(sql_type, Float):
        return NUMBER_KIND, ()
    if isinstance(sql_type, String):
        return TEXT_KIND, ()
    return None


def scalar(value: object) -> ScalarValue:
    if isinstance(value, Enum):
        return str(value.value)
    return value if isinstance(value, int | float | str | bool) or value is None else str(value)


async def pinned_keys(session: AsyncSession, node_id: int) -> frozenset[str]:
    rows = await session.scalars(select(ModifierRow.target_key).where(ModifierRow.target_node_id == node_id, ModifierRow.source_kind == ModifierSource.PIN))
    return frozenset(rows)


def _resolve(table: str, column: str) -> tuple[ProfileShape, Mapper[Any], str, tuple[str, ...]]:
    shape = shape_of_table(table)
    mapper = profile_mapper(table)
    if shape is None or mapper is None:
        raise NotFoundError(f"{table.replace('_', ' ')} is not a record profile.")
    if column not in shape.columns:
        raise ValidationFailedError(f"{table.replace('_', ' ')} has no {column.replace('_', ' ')}.")
    kind = column_kind(mapper, column)
    if kind is None:
        raise ValidationFailedError(f"{column.replace('_', ' ').capitalize()} is a composite value; edit it from its own panel.")
    return shape, mapper, kind[0], kind[1]


def coerce(mapper: Mapper[Any], column: str, value: ScalarValue) -> Any:
    kind, options = column_kind(mapper, column) or (TEXT_KIND, ())
    nullable = bool(mapper.columns[column].nullable)
    label = column.replace("_", " ")
    if value is None:
        if not nullable:
            raise ValidationFailedError(f"{label.capitalize()} cannot be left empty.")
        return None
    if kind == CHOICE_KIND:
        if str(value) not in options:
            raise ValidationFailedError(f"{label.capitalize()} must be one of {', '.join(options)}.")
        enum_class = getattr(mapper.columns[column].type, "enum_class", None)
        return enum_class(str(value)) if enum_class is not None else str(value)
    if kind == FLAG_KIND:
        if not isinstance(value, bool):
            raise ValidationFailedError(f"{label.capitalize()} is yes or no.")
        return value
    if kind == INTEGER_KIND:
        if isinstance(value, bool) or not isinstance(value, int | float) or int(value) != value:
            raise ValidationFailedError(f"{label.capitalize()} must be a whole number.")
        return int(value)
    if kind == NUMBER_KIND:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValidationFailedError(f"{label.capitalize()} must be a number.")
        return float(value)
    return str(value)


async def profile_tables(session: AsyncSession, node_id: int) -> list[ProfileTable]:
    pins = await pinned_keys(session, node_id)
    found: list[ProfileTable] = []
    for mapper in sorted(profile_mappers(), key=table_name):
        shape = shape_of_table(table_name(mapper))
        if shape is None:
            continue
        row = await session.scalar(select(mapper.class_).where(getattr(mapper.class_, shape.node_column) == node_id))
        if row is None:
            continue
        held = held_columns(row)
        columns: list[ProfileColumn] = []
        for column in shape.columns:
            kind = column_kind(mapper, column)
            if kind is None:
                continue
            key = profile_key(shape.table, column)
            nullable = bool(mapper.columns[column].nullable)
            columns.append(ProfileColumn(column, kind[0], scalar(getattr(row, column)), kind[1], nullable, column in held, key in pins))
        found.append(ProfileTable(shape.table, shape.node_column, shape.lockable, tuple(columns)))
    return found


def profile_mappers() -> list[Mapper[Any]]:
    return [mapper for mapper in Base.registry.mappers if shape_of_table(table_name(mapper)) is not None]


async def _row(session: AsyncSession, mapper: Mapper[Any], shape: ProfileShape, node_id: int) -> Any:
    attribute = getattr(mapper.class_, shape.node_column)
    row = await session.scalar(select(mapper.class_).where(attribute == node_id).execution_options(populate_existing=True))
    if row is None:
        raise NotFoundError(f"This record has no {shape.table.replace('_', ' ')}.")
    return row


async def _name(session: AsyncSession, node_id: int) -> str:
    node = await session.get(NodeRow, node_id)
    if node is None:
        raise NotFoundError("No such record.")
    return node.name


@player_action("profile:set", ActionKind.OTHER)
async def set_profile_value(scope: PlayerScope, command: SetProfileValue) -> Effect:
    name = await _name(scope.session, command.node_id)
    shape, mapper, _, _ = _resolve(command.table, command.column)
    row = await _row(scope.session, mapper, shape, command.node_id)
    value = coerce(mapper, command.column, command.value)
    label = command.column.replace("_", " ")
    try:
        async with scope.session.begin_nested():
            setattr(row, command.column, value)
            if command.hold and shape.lockable:
                setattr(row, LOCK_COLUMN, sorted(held_columns(row) | {command.column}))
            await scope.session.flush()
    except IntegrityError as error:
        await scope.session.refresh(row)
        raise ValidationFailedError(f"{label.capitalize()} cannot take the value {command.value}.") from error
    held = " and held" if command.hold else ""
    if command.hold and not shape.lockable:
        await pin_profile(scope, command.node_id, profile_key(shape.table, command.column))
    return Effect(f"{name}'s {label} is now {scalar(value)}{held}.", target_node_id=command.node_id)


async def pin_profile(scope: PlayerScope, node_id: int, key: str) -> None:
    epoch = await scope.epoch()
    await scope.session.execute(
        delete(ModifierRow).where(ModifierRow.target_node_id == node_id, ModifierRow.target_key == key, ModifierRow.source_kind == ModifierSource.PIN)
    )
    await add_modifier(scope.session, ModifierDraft(node_id, key, ModifierOp.ADD, 0, ModifierSource.PIN, "player.pin", start_epoch=epoch))


@player_action("profile:release", ActionKind.OTHER)
async def release_profile_value(scope: PlayerScope, command: ReleaseProfileValue) -> Effect:
    name = await _name(scope.session, command.node_id)
    shape, mapper, _, _ = _resolve(command.table, command.column)
    row = await _row(scope.session, mapper, shape, command.node_id)
    key = profile_key(shape.table, command.column)
    held = held_columns(row)
    unpinned = await scope.session.execute(
        delete(ModifierRow).where(ModifierRow.target_node_id == command.node_id, ModifierRow.target_key == key, ModifierRow.source_kind == ModifierSource.PIN)
    )
    released = int(getattr(unpinned, "rowcount", 0) or 0)
    if command.column in held:
        setattr(row, LOCK_COLUMN, sorted(held - {command.column}))
        released += 1
    label = command.column.replace("_", " ")
    if not released:
        raise ValidationFailedError(f"{name}'s {label} is not held.")
    return Effect(f"{name}'s {label} follows the world again.", target_node_id=command.node_id)
