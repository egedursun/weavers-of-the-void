from pydantic import Field

from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.services.search import GraphLink, GraphNode


class GraphWindow(ApiModel):
    nodes: list[GraphNode]
    links: list[GraphLink]
    node_total: int
    link_total: int
    node_offset: int
    link_offset: int


class FateLinkRequest(RequestModel):
    related: bool = True
    full: bool = False
    entity_ids: list[int] = Field(default_factory=list)


class RepairResult(ApiModel):
    counters: dict[str, int]
    ledger_entry_id: int | None
