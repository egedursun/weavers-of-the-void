from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mortal import CrimeKind, PunishmentKind
from aerona.domain.enums.polity import (
    ClaimBasis,
    ClauseKind,
    DecisionRule,
    GovernmentKind,
    LawArea,
    LawKind,
    LegitimacyBasis,
    OathKind,
    OathPenalty,
    OathStatus,
    OfficeKind,
    PartyRole,
    RegionalStanding,
    TreatyKind,
    TreatyStatus,
)
from aerona.domain.enums.settlement import TreasuryEntry


class NamedNode(ApiModel):
    id: int
    name: str


class MemberView(ApiModel):
    id: int
    name: str
    entity_type: EntityType
    autonomy: int
    population: int
    locked: list[str]


class TerritoryView(ApiModel):
    region_id: int
    name: str
    control: int
    province: str | None
    locked: list[str]


class BalanceSlice(ApiModel):
    id: int
    name: str
    kind: str
    share: int


class RealmLoanView(ApiModel):
    id: int
    lender_id: int
    lender: str
    principal: int
    interest_pct: int
    repaid: int
    due_epoch: int
    status: LoanStatus


class VassalView(ApiModel):
    id: int
    name: str
    overlord_id: int
    tribute_pct: int
    levy_pct: int
    loyalty: int
    treaty_id: int | None
    locked: list[str]


class ReputeView(ApiModel):
    mortal_id: int
    honour: int
    infamy: int
    locked: list[str]


class SentenceView(ApiModel):
    id: int
    mortal_id: int
    mortal: str
    settlement_id: int | None
    crime: CrimeKind
    penalty: PunishmentKind
    epoch: int


class OfficeView(ApiModel):
    id: int
    kind: OfficeKind
    holder_id: int | None
    holder: str | None
    region_id: int | None
    region: str | None
    since_epoch: int
    title: str | None
    powers: list[str]
    target_id: int | None
    target: str | None
    locked: list[str]


class WhyPart(ApiModel):
    label: str
    value: int


class LawView(ApiModel):
    id: int
    name: str
    kind: LawKind
    area: LawArea
    params: dict[str, int | str | bool]
    effect: str
    enforcement: int
    conflict: int
    legitimacy_basis: LegitimacyBasis
    justice: int
    enacted_epoch: int
    holder_id: int | None
    locked: list[str]


class ClaimView(ApiModel):
    id: int
    claimant_id: int
    claimant: str
    house_id: int | None
    polity_id: int
    strength: int
    basis: ClaimBasis
    pressed: bool
    since_epoch: int
    office: OfficeKind
    backer_id: int | None
    locked: list[str]


class TreasuryLineView(ApiModel):
    epoch: int
    entry: TreasuryEntry
    amount: int
    balance: int
    note: str | None


class TreatyBrief(ApiModel):
    id: int
    name: str
    kind: TreatyKind
    status: TreatyStatus
    until_epoch: int | None


class RealmView(ApiModel):
    id: int
    name: str
    government: GovernmentKind
    decision_rule: DecisionRule
    legitimacy: int
    stability: int
    treasury: int
    debt: int
    war_chest: int
    administration: int
    overextension: int
    war_weariness: int
    tier: int
    standing: RegionalStanding
    core: NamedNode | None
    capital: NamedNode | None
    state_religion: NamedNode | None
    ruler: NamedNode | None
    patron_son_id: int | None
    emblem: dict[str, str]
    locked: list[str]
    members: list[MemberView]
    territory: list[TerritoryView]
    offices: list[OfficeView]
    why: list[WhyPart]
    succession: list[NamedNode]
    laws: list[LawView]
    claims: list[ClaimView]
    treasury_ledger: list[TreasuryLineView]
    treaties: list[TreatyBrief]
    overlord: NamedNode | None
    vassals: list[NamedNode]
    tier_strain: int
    power_balance: list[BalanceSlice]
    loans: list[RealmLoanView]
    vassal_terms: list[VassalView]
    overlord_terms: VassalView | None
    ruler_repute: ReputeView | None
    sentences: list[SentenceView]


class RealmLink(ApiModel):
    polity_id: int | None


class HouseMemberView(ApiModel):
    id: int
    name: str
    alive: bool
    sex: SexKind | None
    age: int | None
    parents: list[int]
    by_marriage: bool
    lasting_injuries: int
    fate: str | None
    office: OfficeKind | None


class HeirloomView(ApiModel):
    id: int
    name: str
    since_epoch: int


class HouseView(ApiModel):
    id: int
    name: str
    prestige: int
    wealth: int
    motto: str | None
    emblem: dict[str, str]
    traits: list[str]
    founder: NamedNode | None
    head: NamedNode | None
    parent: NamedNode | None
    polity: NamedNode | None
    divine_son_id: int | None
    branches: list[NamedNode]
    members: list[HouseMemberView]
    claims: list[ClaimView]
    heirlooms: list[HeirloomView]
    locked: list[str]


class PartyView(ApiModel):
    id: int
    name: str
    role: PartyRole


class ClauseView(ApiModel):
    id: int
    kind: ClauseKind
    obligor_id: int | None
    obligor: str | None
    beneficiary_id: int | None
    beneficiary: str | None
    params: dict[str, int | str | bool]
    last_kept_epoch: int | None
    locked: list[str]


class BreachView(ApiModel):
    epoch: int
    breaker_id: int | None
    breaker: str | None
    note: str | None


class TreatyView(ApiModel):
    id: int
    name: str
    kind: TreatyKind
    status: TreatyStatus
    signed_epoch: int
    until_epoch: int | None
    ended_epoch: int | None
    witness_son_id: int | None
    renewals: int
    parties: list[PartyView]
    clauses: list[ClauseView]
    breaches: list[BreachView]
    locked: list[str]
    proposed_by_id: int | None


class OathView(ApiModel):
    id: int
    kind: OathKind
    status: OathStatus
    swearer_id: int
    swearer: str
    recipient_id: int | None
    recipient: str | None
    witness_son_id: int | None
    witness_node_id: int | None = None
    witness: str | None = None
    penalty: OathPenalty | None = None
    sworn_epoch: int
    deadline_epoch: int | None
    ended_epoch: int | None
    note: str | None


class OathsView(ApiModel):
    entity_id: int
    sworn: list[OathView]
    received: list[OathView]


class LawParamSpec(ApiModel):
    key: str
    kind: str
    default: int | str | bool
    low: int
    high: int
    choices: list[str]


class LawKindSpec(ApiModel):
    kind: LawKind
    area: LawArea
    params: list[LawParamSpec]
