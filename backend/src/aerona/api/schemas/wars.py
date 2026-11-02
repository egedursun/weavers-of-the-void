from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.society import CommunityRelationLabel
from aerona.domain.enums.war import BattleOutcome, CaptiveStatus, SiegeStatus, TributeStatus, WarCause, WarEnding, WarSide, WarStatus


class WarSideView(ApiModel):
    entity: NodeRef | None
    side: WarSide
    joined_epoch: int
    left_epoch: int | None


class WarSummary(ApiModel):
    id: int
    event: NodeRef | None
    world_id: int
    status: WarStatus
    cause: WarCause
    cause_text: str | None
    started_epoch: int
    ended_epoch: int | None
    last_clash_epoch: int | None
    battles: int
    score: int
    violence: int | None
    ending: WarEnding | None
    victor: NodeRef | None
    loser: NodeRef | None
    sides: list[WarSideView]


class ArmyView(ApiModel):
    army: NodeRef | None
    war_id: int | None
    owner: NodeRef | None
    commander: NodeRef | None
    raised_epoch: int
    disbanded_epoch: int | None


class BattleView(ApiModel):
    id: int
    war_id: int
    epoch: int
    sequence: int
    record: NodeRef | None
    place: NodeRef | None
    winner: NodeRef | None
    loser: NodeRef | None
    outcome: BattleOutcome
    gap: float
    siege_id: int | None


class SiegeView(ApiModel):
    id: int
    war_id: int
    besieged: NodeRef | None
    besieger: NodeRef | None
    status: SiegeStatus
    started_epoch: int
    ended_epoch: int | None
    rounds: int


class CaptiveView(ApiModel):
    id: int
    captive: NodeRef | None
    captor: NodeRef | None
    home: NodeRef | None
    war_id: int | None
    status: CaptiveStatus
    taken_epoch: int
    released_epoch: int | None
    ransom_paid: int | None


class TributeView(ApiModel):
    id: int
    payer: NodeRef | None
    receiver: NodeRef | None
    war_id: int | None
    status: TributeStatus
    since_epoch: int
    ended_epoch: int | None


class HeroView(ApiModel):
    hero: NodeRef
    role: MortalRole | None
    entity_type: EntityType
    power: int | None


class RelationEventView(ApiModel):
    epoch: int
    event: str
    delta: int


class RelationEntry(ApiModel):
    other: NodeRef
    value: int
    label: CommunityRelationLabel
    blood_feud_since_epoch: int | None
    history: list[RelationEventView]


class RelationList(ApiModel):
    entity_id: int
    relations: list[RelationEntry]


class RelationPair(ApiModel):
    first: NodeRef
    second: NodeRef
    value: int
    label: CommunityRelationLabel
    blood_feud_since_epoch: int | None
    history: list[RelationEventView]
