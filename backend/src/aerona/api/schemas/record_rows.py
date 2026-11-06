from typing import Any

from aerona.api.schemas.common import ApiModel


class ThingRecordColumnView(ApiModel):
    name: str
    kind: str
    options: list[str]
    nullable: bool
    primary: bool
    owner: bool
    required: bool
    editable: bool


class ThingRecordRowView(ApiModel):
    key: dict[str, Any]
    values: dict[str, Any]
    held: list[str]


class ThingRecordTableView(ApiModel):
    table: str
    label: str
    columns: list[ThingRecordColumnView]
    rows: list[ThingRecordRowView]


class ThingRecordNodeView(ApiModel):
    name: str
    link: str


class ThingRecordsView(ApiModel):
    node_id: int
    tables: list[ThingRecordTableView]
    creatable: list[ThingRecordTableView]
    names: dict[str, ThingRecordNodeView]
