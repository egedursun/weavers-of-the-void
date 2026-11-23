from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.divine import (
    BargainGain,
    BargainPrice,
    CouncilMotion,
    DivineWoundKind,
    DomainActivity,
    DomainHook,
    GoalSource,
    GoalState,
    GodGoalKind,
    LawException,
    LawScope,
    OuterHunger,
    PenanceDeed,
    SonPunishment,
    VotingRule,
    WoundCause,
)
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import PerceivedAlignment, WorshipMode
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.son import ExistenceMode


class DomainHookView(ApiModel):
    hook: DomainHook
    label: str
    effect: str
    weight: int
    pct: float
    harmful: bool = False


class DivineDomainView(ApiModel):
    domain: Domain
    label: str
    activity: DomainActivity
    activity_label: str
    severed: bool
    hooks: list[DomainHookView]


class DomainSynergyView(ApiModel):
    label: str
    hook: DomainHook
    hook_label: str


class DomainActivityPoint(ApiModel):
    epoch: int
    domain: Domain
    activity: DomainActivity
    count: int
    essence: int


class GodGoalView(ApiModel):
    id: int
    kind: GodGoalKind
    label: str
    target: NodeRef | None = None
    world: NodeRef | None = None
    domain: Domain | None = None
    amount: int
    progress: int
    state: GoalState
    source: GoalSource
    since_epoch: int
    closed_epoch: int | None = None
    locked: list[str]


class DivineStandingView(ApiModel):
    community: NodeRef
    god: NodeRef
    awe: int
    love: int
    fear: int
    neglect: int
    perceived: PerceivedAlignment | None
    mode: WorshipMode | None
    epoch: int
    locked: list[str]


class DivineWoundView(ApiModel):
    id: int
    kind: DivineWoundKind
    label: str
    domain: Domain | None = None
    severity: int
    healed: int
    cause: WoundCause
    cause_node: NodeRef | None = None
    epoch: int
    prior_mode: ExistenceMode | None = None
    locked: list[str]


class GodAvatarView(ApiModel):
    avatar: NodeRef
    god: NodeRef
    world: NodeRef | None = None
    since_epoch: int
    deeds: int
    alive: bool
    locked: list[str]


class GodDivinity(ApiModel):
    god: NodeRef
    domains: list[DivineDomainView]
    synergy: DomainSynergyView | None = None
    activity: list[DomainActivityPoint]
    goals: list[GodGoalView]
    standing: list[DivineStandingView]
    wounds: list[DivineWoundView]
    avatars: list[GodAvatarView]
    goal_kinds: list[GodGoalKind]


class CommunityRegard(ApiModel):
    community: NodeRef
    standing: list[DivineStandingView]


class CreatorTabooView(ApiModel):
    act: ActKind
    label: str
    severity: int
    since_epoch: int
    broken: int
    last_broken_epoch: int | None = None
    last_breaker: NodeRef | None = None


class WorldAttentionView(ApiModel):
    world: NodeRef
    attention: int
    watched: bool
    far: bool
    epoch: int
    locked: list[str]


class CreatorDivinity(ApiModel):
    taboos: list[CreatorTabooView]
    attention: list[WorldAttentionView]
    standing: list[DivineStandingView]
    far_below: int


class WorldHookView(ApiModel):
    domain: Domain
    hook: DomainHook
    label: str
    pct: int


class WorldDivinity(ApiModel):
    world: NodeRef
    hooks: list[WorldHookView]
    attention: WorldAttentionView | None = None


class CouncilRulingView(ApiModel):
    id: int
    motion: CouncilMotion
    label: str
    target: NodeRef | None = None
    world: NodeRef | None = None
    school: MagicSchool | None = None
    punishment: SonPunishment | None = None
    penance_deed: PenanceDeed | None = None
    voting_rule: VotingRule | None = None
    epoch: int
    until_epoch: int | None = None
    active: bool
    enacted: bool
    note: str | None = None
    locked: list[str]


class CouncilRulings(ApiModel):
    rulings: list[CouncilRulingView]
    motions: list[CouncilMotion]


class NaturalLawProfileView(ApiModel):
    law: NodeRef
    effect: NaturalLaw
    effect_label: str
    effect_text: str
    scope: LawScope
    world: NodeRef | None = None
    region: NodeRef | None = None
    strength: int
    stability: int
    author: NodeRef | None = None
    exception: LawException
    exempt_kind: NodeRef | None = None
    contested: bool
    updated_epoch: int
    drafted: bool = False
    locked: list[str]


class BreachPointView(ApiModel):
    id: int
    world: NodeRef | None = None
    region: NodeRef | None = None
    strength: int
    opened_epoch: int
    locked: list[str]


class OuterBargainView(ApiModel):
    son: NodeRef
    epoch: int
    terms: str | None = None
    gain: BargainGain
    price: BargainPrice
    price_domain: Domain | None = None
    price_world: NodeRef | None = None
    paid: bool


class OuterBeingProfileView(ApiModel):
    being: NodeRef
    hunger: OuterHunger
    hunger_label: str
    reach: int
    fed: int
    oppose_cost: int
    updated_epoch: int
    drafted: bool = False
    locked: list[str]
    breaches: list[BreachPointView]
    bargains: list[OuterBargainView]
