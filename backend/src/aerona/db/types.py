from datetime import UTC, datetime
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import JSON, ColumnElement, DateTime, func, or_
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class PydanticJSON[T](TypeDecorator[T]):
    impl = JSON
    cache_ok = True

    def __init__(self, shape: Any) -> None:
        super().__init__()
        self.shape = shape
        self.adapter: TypeAdapter[T] = TypeAdapter(shape)

    def process_bind_param(self, value: T | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        return self.adapter.dump_python(value, mode="json")

    def process_result_value(self, value: Any, dialect: Dialect) -> T | None:
        if value is None:
            return None
        return self.adapter.validate_python(value)

    def coerce_compared_value(self, op: Any, value: Any) -> Any:
        return JSON()


JSON_NULL = "null"


def json_missing(column: Any) -> ColumnElement[bool]:
    return or_(column.is_(None), func.json_type(column) == JSON_NULL)


class UtcDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
