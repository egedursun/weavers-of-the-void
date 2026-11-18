from pydantic import Field

from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import ChronicleLineRecord


class ChronicleFeedGroup(ApiModel):
    epoch: int
    size: int
    line_ids: list[int]


class ChroniclePage(ApiModel):
    items: list[ChronicleLineRecord]
    total: int
    groups: list[ChronicleFeedGroup] = Field(default_factory=list)


class ChronicleEpoch(ApiModel):
    epoch: int
    name: str | None
    lines: int


class PerspectiveLine(ApiModel):
    id: int
    epoch: int
    people_id: int
    people_name: str | None
    historian: str | None
    historian_entity_id: int | None
    text: str
