from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.law_depth import CourtLevel, JurisdictionClaim, KillMethod, LegalSystem, MoleHuntOutcome, RecruitMotive, RegistryKind
from aerona.domain.enums.mortal import CrimeKind


class LegalSystemView(ApiModel):
    system: LegalSystem
    since_epoch: int
    locked: list[str]


class PrecedentView(ApiModel):
    id: int
    crime: CrimeKind
    verdict: Verdict
    court: CourtLevel
    case_id: int | None
    authority: int
    overturned: bool
    epoch: int
    locked: list[str]


class AppealView(ApiModel):
    case_id: int
    accused: NodeRef | None
    crime: CrimeKind
    from_court: CourtLevel
    to_court: CourtLevel
    fee: int
    filed_epoch: int
    decided_epoch: int | None
    reversed: bool
    locked: list[str]


class OracleCaseView(ApiModel):
    case_id: int
    accused: NodeRef | None
    crime: CrimeKind
    oracle_answer: Verdict | None


class RegistryView(ApiModel):
    id: int
    holder: NodeRef | None
    kind: RegistryKind
    owner: NodeRef | None
    counterparty: NodeRef | None
    subject: NodeRef | None
    amount: int
    registered_epoch: int
    locked: list[str]


class JurisdictionView(ApiModel):
    holder: NodeRef | None
    claimant: NodeRef | None
    claim: JurisdictionClaim
    strength: int
    since_epoch: int
    locked: list[str]


class PardonView(ApiModel):
    id: int
    granter: NodeRef | None
    pardoned: NodeRef | None
    case_id: int | None
    amnesty: bool
    corrupt: bool
    epoch: int


class OutlawView(ApiModel):
    mortal: NodeRef | None
    polity: NodeRef | None
    bounty: int
    private_bounty: int
    renown: int
    declared_epoch: int
    locked: list[str]


class PrisonView(ApiModel):
    structure: NodeRef | None
    food: int
    crowding: int
    cruelty: int
    gang_strength: int
    locked: list[str]


class PrisonerView(ApiModel):
    mortal: NodeRef | None
    prison: NodeRef | None
    case_id: int | None
    term: int
    gang_rank: int
    since_epoch: int
    locked: list[str]


class AgentMotiveView(ApiModel):
    agent_id: int
    mortal: NodeRef | None
    network_id: int
    motive: RecruitMotive
    loyalty: int
    cell_id: int | None


class CellView(ApiModel):
    id: int
    network_id: int
    handler: NodeRef | None
    safe_house: NodeRef | None
    dead_drops: int
    locked: list[str]


class NetworkChoice(ApiModel):
    id: int
    owner: NodeRef | None
    target: NodeRef | None


class MoleHuntView(ApiModel):
    id: int
    polity: NodeRef | None
    spymaster: NodeRef | None
    suspect: NodeRef | None
    mole: bool
    outcome: MoleHuntOutcome
    epoch: int


class DefectionView(ApiModel):
    id: int
    defector: NodeRef | None
    from_side: NodeRef | None
    to_side: NodeRef | None
    secrets: int
    protected: bool
    epoch: int
    locked: list[str]


class KillingView(ApiModel):
    id: int
    victim: NodeRef | None
    killer: NodeRef | None
    method: KillMethod
    recognised: bool
    examiner: NodeRef | None
    epoch: int
    locked: list[str]


class NodeLawView(ApiModel):
    node: NodeRef
    system: LegalSystemView | None
    precedents: list[PrecedentView]
    appeals: list[AppealView]
    oracle_cases: list[OracleCaseView]
    registries: list[RegistryView]
    jurisdictions: list[JurisdictionView]
    pardons: list[PardonView]
    outlaws: list[OutlawView]
    prison: PrisonView | None
    prisons_here: list[NodeRef]
    prisoners: list[PrisonerView]
    agents: list[AgentMotiveView]
    cells: list[CellView]
    networks: list[NetworkChoice]
    hunts: list[MoleHuntView]
    defections: list[DefectionView]
    killings: list[KillingView]
