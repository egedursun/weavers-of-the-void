from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import DriftCause, LabourReason, LoyaltyPart, MobilityEvent, ShortfallEffect


class NeedView(ApiModel):
    social_class: SocialClass
    commodity: CommodityKind
    effect: ShortfallEffect
    wanted: int
    got: int
    held_pct: int | None


class ClassStandingView(ApiModel):
    social_class: SocialClass
    share: float
    satisfaction: int
    fed_pct: int
    needs_met_pct: int
    luxury_pct: int
    wealth: int
    per_head: int
    income: int
    locked: list[str]


class EffectView(ApiModel):
    effect: ShortfallEffect
    short_pct: int


class LabourReasonView(ApiModel):
    job: Job
    reason: LabourReason
    workers: int
    commodity: CommodityKind | None
    workshop: WorkshopKind | None
    price_pct: int


class PriceView(ApiModel):
    commodity: CommodityKind
    price_pct: int


class CorveeView(ApiModel):
    share_pct: int
    polity_id: int | None
    since_epoch: int
    by_hand: bool


class DriftCauseView(ApiModel):
    cause: DriftCause
    axis: ValueAxis
    amount: int
    total: int
    epoch: int


class ImpositionView(ApiModel):
    id: int
    cause: DriftCause
    axis: ValueAxis
    amount: int
    epochs_left: int
    created_epoch: int


class LoyaltyPartView(ApiModel):
    part: LoyaltyPart
    value: int
    grievance: bool


class LoyaltyView(ApiModel):
    polity_id: int
    polity: str
    value_distance: int
    distance_penalty: int
    grievances: int
    benefits: int
    satisfaction: int
    loyalty: int
    autonomy: int
    parts: list[LoyaltyPartView]
    locked: list[str]


class MobilityEventView(ApiModel):
    id: int
    event: MobilityEvent
    count: int
    mortal_id: int | None
    mortal: str
    house_id: int | None
    house: str
    other_id: int | None
    other: str
    by_hand: bool
    epoch: int


class SocietyDepthView(ApiModel):
    entity_id: int
    gini: int
    staples: list[CommodityKind]
    needs: list[NeedView]
    classes: list[ClassStandingView]
    effects: list[EffectView]
    labour_reasons: list[LabourReasonView]
    held_jobs: list[Job]
    prices: list[PriceView]
    corvee: CorveeView | None
    drift_causes: list[DriftCauseView]
    impositions: list[ImpositionView]
    loyalty: list[LoyaltyView]
    mobility: list[MobilityEventView]
