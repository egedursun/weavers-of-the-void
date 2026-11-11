from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.justice import CaseStage, Deposition, ProposalEvent, ProposalStance, ProposalState, TrialKind, Verdict
from aerona.domain.enums.law_depth import CourtLevel
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import LawKind, LegitimacyBasis


class StanceView(ApiModel):
    voice: NodeRef
    stance: ProposalStance
    weight: int
    hooked: bool
    locked: bool


class LawProposalView(ApiModel):
    id: int
    polity: NodeRef | None
    kind: LawKind
    title: str
    params: dict[str, int | str | bool]
    champion: NodeRef | None
    law: NodeRef | None
    basis: LegitimacyBasis
    progress: int
    support: int
    opposition: int
    stalled_epochs: int
    stall_limit: int
    state: ProposalState
    last_event: ProposalEvent | None
    amended: bool
    proposed_epoch: int
    resolved_epoch: int | None
    locked: list[str]
    stances: list[StanceView]


class WitnessView(ApiModel):
    witness: NodeRef
    testimony: Deposition
    reliability: int
    locked: bool


class CrimeCaseView(ApiModel):
    id: int
    crime: CrimeKind
    settlement: NodeRef | None
    polity: NodeRef | None
    culprit: NodeRef | None
    accused: NodeRef | None
    investigator: NodeRef | None
    judge: NodeRef | None
    advocate: NodeRef | None
    court: CourtLevel
    oracle_answer: Verdict | None
    stage: CaseStage
    trial: TrialKind | None
    evidence: int
    standard: int
    tortured: bool
    forged: bool
    verdict: Verdict | None
    wrongful: bool
    penalty: str | None
    opened_epoch: int
    closed_epoch: int | None
    locked: list[str]
    witnesses: list[WitnessView]


class JusticeView(ApiModel):
    node_id: int
    is_realm: bool
    is_city: bool
    is_mortal: bool
    home: NodeRef | None
    proposals: list[LawProposalView]
    cases: list[CrimeCaseView]
