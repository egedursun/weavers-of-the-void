from enum import Enum
from typing import Any

from sqlalchemy import CheckConstraint
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


def table_args(*items: Any) -> tuple[Any, ...]:
    return tuple(items)
