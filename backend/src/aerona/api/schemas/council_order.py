from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.divine import CouncilMotion, CouncilSeat, EscalationStep, VotingRule


class CouncilProcedureView(ApiModel):
    quorum_pct: int
    voting_rule: VotingRule
    creator_veto: bool
    term_epochs: int
    veto_cost: int
    locked: list[str]


class DivineSeatView(ApiModel):
    god: NodeRef
    is_son: bool
    seat: CouncilSeat
    since_epoch: int
    excluded_until: int | None
    sitting: bool
    locked: list[str]


class CouncilViolationView(ApiModel):
    id: int
    ruling_id: int | None
    ruling_motion: CouncilMotion | None
    violator: NodeRef
    epoch: int
    step: EscalationStep
    locked: list[str]


class CouncilOrderView(ApiModel):
    procedure: CouncilProcedureView
    seats: list[DivineSeatView]
    violations: list[CouncilViolationView]


class GodCouncilView(ApiModel):
    node: NodeRef
    is_god: bool
    seat: DivineSeatView | None
    violations: list[CouncilViolationView]
