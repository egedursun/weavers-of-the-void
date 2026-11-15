from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.fossil import FossilReading, FossilSource


class FossilBedView(ApiModel):
    id: int
    region: NodeRef | None
    source: FossilSource
    source_node: NodeRef | None
    richness: int
    frozen: bool
    disease: NodeRef | None
    laid_epoch: int
    found_epoch: int | None
    finder: NodeRef | None
    reading: FossilReading
    locked: list[str]


class FossilNodeView(ApiModel):
    node: NodeRef
    region: NodeRef | None
    beds: list[FossilBedView]
    world_found: int
    world_hidden: int
    absent_reason: str | None
