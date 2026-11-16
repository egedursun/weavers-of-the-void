from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.cosmography import DimensionElement
from aerona.domain.enums.ecology import AttackDelivery, AttackEffect, AttackRange
from aerona.domain.enums.horror import HorrorEffect, HorrorScope, HorrorSense, HorrorSource, HorrorTarget
from aerona.domain.enums.quests import QuestAim, QuestObstacle, QuestReward, QuestScale, QuestTargetKind
from aerona.domain.enums.war import HeroQuestStatus


class HorrorEventView(ApiModel):
    id: int
    world: NodeRef
    name: str | None
    target: HorrorTarget
    effect: HorrorEffect
    scope: HorrorScope
    sense: HorrorSense
    source: HorrorSource
    source_node: NodeRef | None
    subject: NodeRef | None
    duration: int
    sanity_cost: int
    leak: int
    epoch: int
    until_epoch: int | None
    locked: list[str]


class CreatureAttackRecord(ApiModel):
    id: int
    delivery: AttackDelivery
    effect: AttackEffect
    range: AttackRange
    recharge: int
    permanent: bool
    last_used_epoch: int | None
    locked: list[str]


class HeroQuestView(ApiModel):
    id: int
    aim: QuestAim
    target_kind: QuestTargetKind
    obstacle: QuestObstacle
    reward: QuestReward
    scale: QuestScale
    target: NodeRef | None
    description: str
    status: HeroQuestStatus
    started_epoch: int
    ended_epoch: int | None
    locked: list[str]


class AspectView(ApiModel):
    id: int
    form: SpellForm | None
    element: DimensionElement | None
    strength: int
    locked: list[str]


class TypedModelsView(ApiModel):
    node: NodeRef
    is_dimension: bool
    horrors: list[HorrorEventView]
    attacks: list[CreatureAttackRecord]
    quests: list[HeroQuestView]
    aspects: list[AspectView]
