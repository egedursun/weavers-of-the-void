from aerona.api.schemas.common import ApiModel


class ProfileColumnRecord(ApiModel):
    name: str
    kind: str
    value: int | float | str | bool | None
    options: list[str]
    nullable: bool
    held: bool
    pinned: bool


class ProfileTableRecord(ApiModel):
    table: str
    lockable: bool
    columns: list[ProfileColumnRecord]
