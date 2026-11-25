from datetime import datetime
from typing import Any

from pydantic import Field

from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.presence import PresenceEventKind, PresenceExchangeStatus, PresenceGuise, PresenceRecord, PresenceStatus, SpeakerGroup
from aerona.domain.enums.son import SonDeathCause, SonStatus

PLAYER_TEXT_MAX = 20000


class PresenceOpenRequest(RequestModel):
    node_id: int = Field(ge=1)
    guise: PresenceGuise
    record: PresenceRecord


class PresenceSayRequest(RequestModel):
    text: str = Field(min_length=1, max_length=PLAYER_TEXT_MAX)


class PresenceSpeakerItem(ApiModel):
    node_id: int
    name: str
    kind: NodeKind
    entity_type: EntityType | None
    group: SpeakerGroup
    dead: bool
    cover: str | None
    open_session_id: int | None


class PresenceSpeakerPage(ApiModel):
    speakers: list[PresenceSpeakerItem]
    total: int
    offset: int
    limit: int
    has_more: bool


class PresenceSpeakerCard(ApiModel):
    node_id: int
    name: str
    epithet: str
    kind: NodeKind
    entity_type: EntityType | None
    group: SpeakerGroup
    son_status: SonStatus | None
    foreign_god_status: ForeignGodStatus | None
    entity_status: EntityStatus | None
    place_name: str
    world_name: str
    patron_name: str
    faith: int | None
    languages: list[str]
    dead: bool
    death_epoch: int | None
    son_death_cause: SonDeathCause | None
    mortal_death_cause: DeathCause | None
    death_line: str
    cover: str | None
    can_act: bool


class PresenceSessionSummary(ApiModel):
    id: int
    node_id: int
    guise: PresenceGuise
    record: PresenceRecord
    status: PresenceStatus
    dead_when_summoned: bool
    title: str
    opened_epoch: int
    opened_at: datetime
    closed_at: datetime | None
    exchange_count: int


class PresenceSpeakerView(ApiModel):
    card: PresenceSpeakerCard
    open_session: PresenceSessionSummary | None
    past_sessions: list[PresenceSessionSummary]
    model_enabled: bool
    remembered_exchanges: int


class PresenceEventView(ApiModel):
    id: int
    ordinal: int
    kind: PresenceEventKind
    tool: str
    payload: dict[str, Any]
    created_at: datetime


class PresenceExchangeView(ApiModel):
    id: int
    session_id: int
    ordinal: int
    epoch: int
    player_text: str
    reply_text: str
    remember_text: str
    status: PresenceExchangeStatus
    error: str
    model: str
    input_tokens: int
    output_tokens: int
    steps: int
    started_at: datetime
    finished_at: datetime | None
    events: list[PresenceEventView]


class PresenceSessionView(ApiModel):
    session: PresenceSessionSummary
    exchanges: list[PresenceExchangeView]
    memory_boundary: int
    remembered_exchanges: int
    running_exchange_id: int | None


class PresenceExchangeAccepted(ApiModel):
    exchange_id: int
    session_id: int
    ordinal: int


class PresenceClosedView(ApiModel):
    session_id: int
    node_id: int
    kept: bool
