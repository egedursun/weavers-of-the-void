from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import (
    ClaimBasis,
    ClauseKind,
    DecisionRule,
    GovernmentKind,
    LawArea,
    LawKind,
    LegitimacyBasis,
    OathKind,
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


class TerritoryView(ApiModel):
    region_id: int
    name: str
    control: int


class OfficeView(ApiModel):
    id: int
    kind: OfficeKind
    holder_id: int | None
    holder: str | None
    region_id: int | None
    region: str | None
    since_epoch: int


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


class RealmLink(ApiModel):
    polity_id: int | None


class HouseMemberView(ApiModel):
    id: int
    name: str
    alive: bool
    sex: str | None
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


class OathView(ApiModel):
    id: int
    kind: OathKind
    status: OathStatus
    swearer_id: int
    swearer: str
    recipient_id: int | None
    recipient: str | None
    witness_son_id: int | None
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
