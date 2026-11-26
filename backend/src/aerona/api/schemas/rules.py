from pydantic import Field

from aerona.api.schemas.common import ApiModel


class RuleResponse(ApiModel):
    namespace: str
    key: str
    value: float
    default: float
    minimum: float
    maximum: float
    group: str
    label: str
    integer: bool
    warning: str | None = None


class RuleValuesResponse(ApiModel):
    values: dict[str, float]


class RuleUpdateRequest(ApiModel):
    value: float


class RuleBatchRequest(ApiModel):
    changes: dict[str, float | None] = Field(default_factory=dict)
    reset_all: bool = False
