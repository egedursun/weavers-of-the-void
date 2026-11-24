from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.enums.mind import ActKind, SkillKind
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, LorePrice, ReputationAxis


class LocalReputationView(ApiModel):
    id: int
    subject: NodeRef | None
    community: NodeRef | None
    axis: ReputationAxis
    label: str
    skill: SkillKind | None
    value: int
    heard_epoch: int
    held: bool


class StandingView(ApiModel):
    prestige: int
    piety: int
    dread: int
    tyranny: int
    trust: int
    learning: int
    silenced_until: int | None
    updated_epoch: int
    realm: NodeRef | None
    held: list[str]


class DeedClaimView(ApiModel):
    id: int
    claimant: NodeRef | None
    kind: ClaimKind
    kind_label: str
    status: ClaimStatus
    status_label: str
    credited: int
    epoch: int
    held: bool


class DeedRecordView(ApiModel):
    id: int
    doer: NodeRef | None
    act: ActKind | None
    axis: ReputationAxis
    label: str
    skill: SkillKind | None
    place: NodeRef | None
    magnitude: int
    witnesses: int
    token: bool
    epoch: int
    note: str | None
    claims: list[DeedClaimView]


class LoreTradeView(ApiModel):
    id: int
    seller: NodeRef | None
    buyer: NodeRef | None
    kind: KnowledgeKind
    kind_label: str
    key: str
    subject: NodeRef | None
    value: int
    price: LorePrice
    price_label: str
    epoch: int


class RenownView(ApiModel):
    node_id: int
    name: str
    glory: int
    infamy: int
    reputations: list[LocalReputationView]
    views: list[LocalReputationView]
    standing: StandingView | None
    ruler: bool
    deeds: list[DeedRecordView]
    trades: list[LoreTradeView]
    axes: list[LabelView]
    claim_kinds: list[LabelView]
    claim_statuses: list[LabelView]
    lore_kinds: list[LabelView]
