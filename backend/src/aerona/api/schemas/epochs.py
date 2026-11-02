from pydantic import Field

from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import EpochRecord


class WorldNarrative(ApiModel):
    world_id: int
    world_name: str
    narrative: str | None
    summary: str | None


class EpochListItem(EpochRecord):
    worlds: list[WorldNarrative] = Field(default_factory=list)
