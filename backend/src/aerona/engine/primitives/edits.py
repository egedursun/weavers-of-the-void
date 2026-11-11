import re
from typing import cast

from sqlalchemy import JSON, Boolean, CheckConstraint, Float, Integer, Table
from sqlalchemy.sql.sqltypes import Enum as SqlEnum

from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base

RANGE = re.compile(r"^(\w+) BETWEEN (-?\d+) AND (-?\d+)$")
FLOOR = re.compile(r"^(\w+) >= (-?\d+)$")
FIXED = frozenset({"updated_epoch", "locked", "resolved_epoch", "since_epoch"})
EMPTY_CHOICE = "none"


def table_of(row: Base) -> Table:
    return cast(Table, type(row).__table__)


def bounds(row: Base) -> dict[str, tuple[int, int | None]]:
    found: dict[str, tuple[int, int | None]] = {}
    for constraint in table_of(row).constraints:
        if not isinstance(constraint, CheckConstraint):
            continue
        text = str(constraint.sqltext)
        if match := RANGE.match(text):
            found[match.group(1)] = (int(match.group(2)), int(match.group(3)))
        elif match := FLOOR.match(text):
            found[match.group(1)] = (int(match.group(2)), None)
    return found


def whole(key: str, value: object, limits: dict[str, tuple[int, int | None]]) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is a whole number.")
    low, high = limits.get(key, (None, None))
    if (low is not None and value < low) or (high is not None and value > high):
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from {low} to {high if high is not None else 'any height'}.")
    return value


def number(key: str, value: object) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is a number.")
    return float(value)


def none_member(kind: object) -> object | None:
    enum_class = getattr(kind, "enum_class", None)
    if enum_class is None:
        return None
    return next((member for member in enum_class if str(getattr(member, "value", "")) == EMPTY_CHOICE), None)


def empty_value(kind: object, nullable: bool, message: str) -> object:
    if nullable:
        return None
    member = none_member(kind)
    if member is None:
        raise ValidationFailedError(message)
    return member


def coerce(row: Base, key: str, value: object, limits: dict[str, tuple[int, int | None]]) -> object:
    column = table_of(row).columns.get(key)
    if column is None or column.primary_key or key in FIXED:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} cannot be set here.")
    kind = column.type
    if value is None:
        return empty_value(kind, bool(column.nullable), f"{key.replace('_', ' ').capitalize()} cannot be empty.")
    if isinstance(kind, SqlEnum) and kind.enum_class is not None:
        try:
            return kind.enum_class(str(value))
        except ValueError as error:
            raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error
    if isinstance(kind, Boolean):
        if not isinstance(value, bool):
            raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is yes or no.")
        return value
    if isinstance(kind, Integer | Float):
        return whole(key, value, limits) if isinstance(kind, Integer) else number(key, value)
    if isinstance(kind, JSON):
        if not isinstance(value, dict | list):
            raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is a list or a table of values.")
        return value
    if not isinstance(value, str):
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is text.")
    return value
