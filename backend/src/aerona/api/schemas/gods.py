from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import (
    BondView,
    ChronicleLineRecord,
    CreatorRecord,
    EntitySummary,
    ForeignGodPower,
    ForeignGodRecord,
    ImageRecord,
    NodeRef,
    SonRecord,
    WorldRecord,
)
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.creator import CreatorMoodAxis, CreatorMoodLabel, CreatorPassion
from aerona.domain.enums.dominion import PrayerTone
from aerona.domain.enums.son import ReputationLabel, SonDeathCause


class MoodInput(ApiModel):
    epoch: int
    axis: CreatorMoodAxis
    item: str
    delta: float


class CreatorMood(ApiModel):
    contentment: int
    anger: int
    interest: int
    loneliness: int
    label: CreatorMoodLabel
    breakdown: list[MoodInput]


class FolkView(ApiModel):
    people_id: int
    people_name: str
    local_name: str | None
    account: str
    misconception: str | None
    epoch: int


class CreatorDetail(ApiModel):
    creator: CreatorRecord
    cover: str | None
    mood: CreatorMood
    faith: int
    cult_essence: int
    cult: list[EntitySummary]
    folk_views: list[FolkView]
    traces: list[ChronicleLineRecord]
    traces_total: int
    images: list[ImageRecord]


class SonReputation(ApiModel):
    son_id: int
    name: str
    love: int
    fear: int
    forgotten: int
    unanswered: int
    last_contact: int
    label: ReputationLabel


class PassionInfo(ApiModel):
    passion: CreatorPassion
    name: str
    hint: str


class CreatorReputation(ApiModel):
    love: int
    fear: int
    forgotten: int
    label: ReputationLabel
    sons: list[SonReputation]
    passions: list[CreatorPassion]
    automatic: bool
    all_passions: list[PassionInfo]


class ForeignGodWorshipper(ApiModel):
    entity: EntitySummary
    cover: str | None


class ForeignGodDetail(ApiModel):
    god: ForeignGodRecord
    powers: list[ForeignGodPower]
    kill_cost: int
    deathless: bool
    deathless_caption: str | None
    drain_amount: int
    drain_gain: int
    world: WorldRecord | None
    worshippers: list[ForeignGodWorshipper]
    bonds: list[BondView]
    bond_total: int
    chronicle: list[ChronicleLineRecord]
    chronicle_total: int
    sons_here: list[NodeRef]
    folk_views: list[FolkView]
    images: list[ImageRecord]
    cover: str | None


class SonDetail(ApiModel):
    son: SonRecord
    kill_cost: int
    reputation: SonReputation | None
    folk_views: list[FolkView]
    creations: list[EntitySummary]
    chronicle: list[ChronicleLineRecord]
    chronicle_total: int
    messages: list["MessageView"]
    siblings: list["SiblingView"]
    bonds: list[BondView]
    bond_total: int
    live_faith: int
    worshippers: list[EntitySummary]
    anchor: EntitySummary | None
    parent: NodeRef | None
    children: list[NodeRef]
    images: list[ImageRecord]


class MessageView(ApiModel):
    id: int
    epoch: int
    sender: NodeRef | None
    recipient: NodeRef | None
    intent: MessageIntent
    text: str
    tone: PrayerTone | None
    answered: bool


class SiblingView(ApiModel):
    son: NodeRef
    value: int
    note: str | None
    cover: str | None


SonDetail.model_rebuild()


class ResurrectionOrder(ApiModel):
    id: int
    name: str
    devotion: int
    followers: int


class DeadSonPanel(ApiModel):
    son_id: int
    name: str
    death_epoch: int | None
    death_cause: SonDeathCause | None
    earliest_return_epoch: int | None
    epochs_remaining: int
    devotion: int
    devotion_required: int
    corpse: EntitySummary | None
    orders: list[ResurrectionOrder]
    loyal_communities: list[EntitySummary]


class DistributionCandidateView(ApiModel):
    son_id: int
    name: str
    world_id: int | None
    score: int
    protected: bool


class DistributionPreviewView(ApiModel):
    candidates: list[DistributionCandidateView]
    next_son_id: int | None
    godless_world_ids: list[int]
