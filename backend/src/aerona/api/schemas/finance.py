from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.finance import CreditState, SpeculationStatus, TradePolicyKind
from aerona.domain.enums.society import SocialClass


class FinanceCreditView(ApiModel):
    rating: int
    state: CreditState
    state_label: str
    interest_pct: int
    reserves: int
    defaults: int
    restructured_until: int | None
    rescuer: NodeRef | None
    rescue_terms: int
    repudiated_until: int | None
    epoch: int
    held: list[str]


class FinancePolicyView(ApiModel):
    id: int
    issuer: NodeRef | None
    kind: TradePolicyKind
    kind_label: str
    commodity: CommodityKind | None
    commodity_label: str
    partner: NodeRef | None
    rate_pct: int
    since_epoch: int
    reason: str | None
    held: bool


class FinanceHoardView(ApiModel):
    id: int
    merchant: NodeRef | None
    market: NodeRef | None
    commodity: CommodityKind
    commodity_label: str
    units: int
    price: int
    status: SpeculationStatus
    status_label: str
    opened_epoch: int
    settled_epoch: int | None
    gain: int
    held: bool


class FinanceLivingView(ApiModel):
    key: SocialClass
    value: int


class FinanceIndicatorView(ApiModel):
    id: int
    epoch: int
    output: int
    price_index: int
    trade_balance: int
    treasury: int
    debt_ratio: int
    unemployment: int
    market_access: int
    black_market: int
    living: list[FinanceLivingView]
    held: list[str]


class FinanceView(ApiModel):
    node_id: int
    name: str
    realm: NodeRef | None
    credit: FinanceCreditView | None
    policies: list[FinancePolicyView]
    hoards: list[FinanceHoardView]
    indicators: list[FinanceIndicatorView]
    market_access: int | None
    black_market: int | None
    policy_kinds: list[LabelView]
    credit_states: list[LabelView]
    commodities: list[LabelView]
