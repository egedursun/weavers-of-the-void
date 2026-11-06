from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.relations import (
    AppealKind,
    CircleKind,
    ContestEnd,
    ContestKind,
    ContestStake,
    GroupKind,
    PassionKind,
    PassionSource,
    PersuasionAim,
    RelationType,
)


class TieView(ApiModel):
    id: int
    subject: NodeRef
    friendship: int
    romance: int
    familiarity: int
    rivalry: int
    their_friendship: int | None
    their_romance: int | None
    kinds: list[RelationType]
    affair: bool
    affair_known: bool
    since_epoch: int
    last_epoch: int
    held: list[str]


class PassionView(ApiModel):
    id: int
    kind: PassionKind
    label: str
    object: NodeRef | None
    strength: int
    source: PassionSource
    source_label: str
    since_epoch: int
    invoked_epoch: int | None
    invocable: bool
    held: bool


class CircleView(ApiModel):
    circle: NodeRef
    kind: CircleKind
    label: str
    taste_key: str | None
    axis: ValueAxis | None
    meeting_place: NodeRef | None
    ideology: NodeRef | None
    founded_epoch: int
    members: list[NodeRef]
    leader: NodeRef | None
    held: list[str]


class RankView(ApiModel):
    group: NodeRef
    group_kind: GroupKind
    group_label: str
    member: NodeRef
    rank: int
    dominance: int
    size: int
    since_epoch: int
    held: list[str]


class ContestView(ApiModel):
    id: int
    kind: ContestKind
    label: str
    stake: ContestStake
    stake_label: str
    challenger: NodeRef | None
    defender: NodeRef | None
    judge: NodeRef | None
    stake_node: NodeRef | None
    place: NodeRef | None
    wager: int
    rounds: list[list[float]]
    outcome: ContestEnd
    famous: bool
    work: NodeRef | None
    epoch: int
    note: str | None


class PersuasionView(ApiModel):
    id: int
    speaker: NodeRef | None
    target: NodeRef | None
    appeal: AppealKind
    appeal_label: str
    aim: PersuasionAim
    aim_label: str
    axis: ValueAxis | None
    subject: NodeRef | None
    score: int
    success: bool
    epoch: int


class BondsView(ApiModel):
    node_id: int
    name: str
    applies: bool
    mortal: bool
    place: bool
    reason: str | None
    bonds_held: bool
    passions_held: bool
    bonds: list[TieView]
    passions: list[PassionView]
    circles: list[CircleView]
    ranks: list[RankView]
    order: list[RankView]
    contests: list[ContestView]
    persuasions: list[PersuasionView]
    relation_types: list[LabelView]
    circle_kinds: list[LabelView]
    passion_kinds: list[LabelView]
    passion_sources: list[LabelView]
    appeals: list[LabelView]
    aims: list[LabelView]
    contest_kinds: list[LabelView]
    stakes: list[LabelView]
    group_kinds: list[LabelView]
