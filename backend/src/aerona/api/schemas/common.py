from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator("*", mode="after")
    @classmethod
    def stored_times_are_utc(cls, value: object) -> object:
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ErrorCode(StrEnum):
    INVALID = "invalid"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    BUSY = "busy"
    READ_ONLY = "read_only"
    INSUFFICIENT = "insufficient"
    FORBIDDEN = "forbidden"
    TOO_LARGE = "too_large"
    UNAVAILABLE = "unavailable"
    INTERNAL = "internal"
    UNIVERSE_REQUIRED = "universe_required"


class ErrorResponse(ApiModel):
    error: str
    code: ErrorCode = ErrorCode.INVALID
    rule_key: str | None = None
    rule_value: float | None = None
    correlation_id: str | None = None


class JobAccepted(ApiModel):
    job_id: str


class Done(ApiModel):
    ok: bool = True
    message: str | None = None


class Page[T](ApiModel):
    items: list[T]
    total: int
    offset: int
    limit: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total
