from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.eras import TechFamily


class TechLevelView(ApiModel):
    family: TechFamily
    level: int
    own: bool
    held: bool


class TechnologyNodeView(ApiModel):
    node: NodeRef
    families: list[TechLevelView]
