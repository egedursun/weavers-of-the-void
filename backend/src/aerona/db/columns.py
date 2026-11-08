import re
from enum import Enum
from functools import cache

from sqlalchemy import CheckConstraint, Table
from sqlalchemy import Enum as SqlEnum

from aerona.constants.schema import ENUM_MAX_LENGTH


def enum_type[E: Enum](enum_class: type[E], name: str) -> SqlEnum:
    return SqlEnum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=ENUM_MAX_LENGTH,
        values_callable=lambda members: [str(member.value) for member in members],
        validate_strings=True,
    )


def between(column: str, low: int, high: int, name: str | None = None) -> CheckConstraint:
    return CheckConstraint(f"{column} BETWEEN {int(low)} AND {int(high)}", name=name or f"{column}_range")


def at_least(column: str, low: int, name: str | None = None) -> CheckConstraint:
    return CheckConstraint(f"{column} >= {int(low)}", name=name or f"{column}_min")


def nullable_between(column: str, low: int, high: int) -> CheckConstraint:
    return CheckConstraint(f"{column} IS NULL OR {column} BETWEEN {int(low)} AND {int(high)}", name=f"{column}_range")


def max_length(column: str, limit: int) -> CheckConstraint:
    return CheckConstraint(f"{column} IS NULL OR length({column}) <= {limit}", name=f"{column}_length")


RANGE = re.compile(r"^(\w+) BETWEEN (-?\d+) AND (-?\d+)$")
FLOOR = re.compile(r"^(\w+) >= (-?\d+)$")


@cache
def column_bounds(table: Table) -> dict[str, tuple[int | None, int | None]]:
    bounds: dict[str, tuple[int | None, int | None]] = {}
    for constraint in table.constraints:
        if not isinstance(constraint, CheckConstraint):
            continue
        text = str(constraint.sqltext)
        if found := RANGE.match(text):
            bounds[found[1]] = (int(found[2]), int(found[3]))
        elif found := FLOOR.match(text):
            bounds[found[1]] = (int(found[2]), bounds.get(found[1], (None, None))[1])
    return bounds


def within_bounds(row: object, column: str, value: int) -> bool:
    table = getattr(type(row), "__table__", None)
    if not isinstance(table, Table):
        return True
    low, high = column_bounds(table).get(column, (None, None))
    return (low is None or value >= low) and (high is None or value <= high)
