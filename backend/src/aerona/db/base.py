from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnDefault, MetaData, event, func, inspect
from sqlalchemy.orm import ColumnProperty, DeclarativeBase, Mapped, mapped_column

from aerona.db.types import UtcDateTime

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


Filler = tuple[str, Callable[[], Any]]
FILLERS: dict[type, tuple[Filler, ...]] = {}


def filler(default: ColumnDefault) -> Callable[[], Any] | None:
    if default.is_scalar:
        value = default.arg
        return lambda: value
    if default.is_callable:
        made = default.arg
        return lambda: made(None)
    return None


def fillers_of(kind: type) -> tuple[Filler, ...]:
    found = FILLERS.get(kind)
    if found is None:
        pairs: list[Filler] = []
        attributes: list[ColumnProperty[Any]] = list(inspect(kind).column_attrs)
        for attribute in attributes:
            column = attribute.columns[0]
            default = column.default
            fill = filler(default) if isinstance(default, ColumnDefault) and not column.primary_key else None
            if fill is not None:
                pairs.append((attribute.key, fill))
        found = FILLERS[kind] = tuple(pairs)
    return found


@event.listens_for(Base, "init", propagate=True)
def fill_defaults(target: Base, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    for key, fill in fillers_of(type(target)):
        if key not in kwargs:
            setattr(target, key, fill())


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now(), onupdate=func.now())
