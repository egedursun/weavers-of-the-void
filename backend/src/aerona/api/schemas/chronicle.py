from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import ChronicleLineRecord


class ChroniclePage(ApiModel):
    items: list[ChronicleLineRecord]
    total: int


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
    text: str
