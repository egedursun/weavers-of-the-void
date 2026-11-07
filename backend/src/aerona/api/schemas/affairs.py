from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import CouncilTask, CourtPosition, MandateKind, MandateState, NobleWant, ResolutionKind, ResolutionState, TaxKind


class CouncilTaskView(ApiModel):
    office_id: int
    office: OfficeKind
    holder: NodeRef | None
    task: CouncilTask | None
    target: NodeRef | None
    diligence: int
    locked: list[str]


class ElectionResultView(ApiModel):
    holder: NodeRef
    share: int


class ElectionView(ApiModel):
    id: int
    epoch: int
    seats: int
    turnout: int
    winner: NodeRef | None
    results: list[ElectionResultView]


class SeatView(ApiModel):
    holder: NodeRef
    seats: int
    votes: int
    since_epoch: int
    locked: bool


class TaxView(ApiModel):
    kind: TaxKind
    rate: int
    farmed: bool
    efficiency: int
    take: int
    locked: list[str]


class MandateView(ApiModel):
    id: int
    polity: NodeRef | None
    issuer: NodeRef | None
    kind: MandateKind
    settlement: NodeRef | None
    commodity: CommodityKind | None
    district: DistrictKind | None
    amount: int
    issued_epoch: int
    until_epoch: int
    state: MandateState
    locked: list[str]


class DemandView(ApiModel):
    noble: NodeRef
    want: NobleWant
    since_epoch: int
    met: bool
    locked: bool


class ApprovalView(ApiModel):
    social_class: SocialClass
    approval: int
    parts: dict[str, int]
    locked: list[str]


class VoteView(ApiModel):
    member: NodeRef
    aye: bool
    weight: int
    locked: bool


class ResolutionView(ApiModel):
    id: int
    assembly: NodeRef | None
    kind: ResolutionKind
    target: NodeRef | None
    votes_for: int
    votes_against: int
    state: ResolutionState
    proposed_epoch: int
    until_epoch: int | None
    locked: list[str]
    votes: list[VoteView]


class PositionView(ApiModel):
    position: CourtPosition
    holder: NodeRef | None
    since_epoch: int
    locked: bool


class CourtView(ApiModel):
    grandeur: int
    courtiers: int
    parts: dict[str, int]
    locked: list[str]


class AffairsView(ApiModel):
    node_id: int
    realm: NodeRef | None
    is_mortal: bool
    corruption: int | None
    corruption_held: bool
    tax_cap: int
    council: list[CouncilTaskView]
    elections: list[ElectionView]
    seats: list[SeatView]
    taxes: list[TaxView]
    mandates: list[MandateView]
    demands: list[DemandView]
    approvals: list[ApprovalView]
    is_assembly: bool
    resolutions: list[ResolutionView]
    court: CourtView | None
    positions: list[PositionView]
