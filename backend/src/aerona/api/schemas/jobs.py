from datetime import datetime
from typing import Any

from pydantic import computed_field, field_serializer

from aerona.api.schemas.common import ApiModel
from aerona.jobs.context import JOB_LABEL_KEY
from aerona.jobs.manager import ITEMS_KEY


class JobItem(ApiModel):
    node_id: int
    node_kind: str
    name: str
    entity_type: str | None = None
    action: str
    note: str | None = None
    other_id: int | None = None
    other_kind: str | None = None
    other_name: str | None = None


class JobResponse(ApiModel):
    id: str
    kind: str
    status: str
    progress: float
    stage: str | None
    params: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @field_serializer("result")
    def result_without_items(self, result: dict[str, Any] | None) -> dict[str, Any] | None:
        if result is None:
            return None
        return {key: value for key, value in result.items() if key != ITEMS_KEY}

    @computed_field
    def label(self) -> str | None:
        value = self.params.get(JOB_LABEL_KEY)
        return value if isinstance(value, str) else None

    @computed_field
    def items(self) -> list[JobItem]:
        raw = (self.result or {}).get(ITEMS_KEY)
        if not isinstance(raw, list):
            return []
        return [JobItem.model_validate(item) for item in raw if isinstance(item, dict)]
