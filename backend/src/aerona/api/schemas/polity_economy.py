from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.material import MaterialKind


class MemberOutputView(ApiModel):
    community_id: int
    name: str
    epoch: int | None
    made: int
    bottlenecks: int
    workshops: int


class PolityChainStepView(ApiModel):
    key: str
    label: str
    workshop: WorkshopKind | None
    inputs: dict[str, int]
    output: CommodityKind
    output_qty: int
    made: int
    quality: int
    material: MaterialKind | None
    bottleneck: CommodityKind | None
    starved_ids: list[int]
    running_ids: list[int]
    able_ids: list[int]


class PolityStockView(ApiModel):
    commodity: CommodityKind
    quantity: int
    quality: int


class PolityProductionView(ApiModel):
    polity_id: int
    name: str
    epoch: int
    members: list[MemberOutputView]
    chain: list[PolityChainStepView]
    stocks: list[PolityStockView]
    workshops: dict[str, int]


class PactView(ApiModel):
    treaty_id: int
    name: str
    status: str
    owner_id: int | None
    owner_name: str
    demand: str
    commodity: CommodityKind | None
    units: int
    cost: int
    every: int
    paid_epoch: int
    signed_epoch: int
    until_epoch: int | None
    misread: bool
