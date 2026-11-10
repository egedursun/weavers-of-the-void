import operator
from datetime import datetime
from functools import reduce
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from aerona.domain.enums.chronicle import FeedCategory
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.rarity import Rarity
from aerona.events.kinds import EventKind


class EventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    epoch: int | None = None


class EmptyPayload(EventPayload):
    pass


class TextPayload(EventPayload):
    text: str


class ErrorPayload(TextPayload):
    will_retry: bool = False
    son_id: int | None = None


class JobPayload(EventPayload):
    job_id: str
    kind: JobKind


class JobProgressPayload(JobPayload):
    progress: float
    stage: str | None = None


class JobFinishedPayload(JobPayload):
    result: dict[str, Any] | None = None


class JobFailedPayload(JobPayload):
    error: str


class WorldChangedPayload(EventPayload):
    action: str | None = None
    target_node_id: int | None = None
    ledger_entry_id: int | None = None


class RulesChangedPayload(EventPayload):
    namespace: str | None = None
    key: str | None = None


class EngineNotePayload(EventPayload):
    phase: str
    kind: str
    text: str
    feed: FeedCategory | None = None


class EnginePhasePayload(EventPayload):
    phase: str
    seconds: float | None = None
    error: str | None = None


class RetryPayload(EventPayload):
    actor: str
    kind: str
    attempt: int
    total: int
    reason: str | None = None
    wait_s: int = 0
    kept_steps: int = 0


class TurnOrderItem(BaseModel):
    id: int
    name: str
    ini: int


class EpochStartedPayload(EventPayload):
    order: list[TurnOrderItem] = Field(default_factory=list)
    resuming: bool = False


class EpochResumedPayload(EventPayload):
    phase: int


class EpochProgressPayload(EventPayload):
    no: int
    total: int
    name: str


class EpochStoppedPayload(EventPayload):
    phase: int


class EpochFinishedPayload(EventPayload):
    new_epoch: int
    summary: dict[str, Any] = Field(default_factory=dict)
    duration_s: int


class FilePayload(EventPayload):
    file: str
    label: str | None = None


class SonDistributedPayload(EventPayload):
    son_id: int | None = None
    world_id: int | None = None
    text: str | None = None
    moved: int | None = None


class SonTurnQueuedPayload(EventPayload):
    no: int
    total: int
    son_id: int
    name: str
    model: str | None = None
    rarity: Rarity | None = None


class SonTurnStartedPayload(EventPayload):
    son_id: int
    son_name: str
    resumed: bool = False
    model: str | None = None
    rarity: Rarity | None = None


class TurnFinishedPayload(EventPayload):
    word: str | None = None
    creations: list[int] = Field(default_factory=list)
    status: str
    model: str | None = None


class SonTurnFinishedPayload(TurnFinishedPayload):
    son_id: int
    son_name: str
    rarity: Rarity | None = None


class MortalAgentItem(BaseModel):
    id: int
    name: str
    type: str


class MortalsStartedPayload(EventPayload):
    agents: list[MortalAgentItem] = Field(default_factory=list)


class MortalTurnStartedPayload(EventPayload):
    entity_id: int
    name: str
    resumed: bool = False
    model: str | None = None
    order: int | None = None
    total: int | None = None


class MortalTurnFinishedPayload(TurnFinishedPayload):
    entity_id: int
    name: str


class EngineFinishedPayload(EventPayload):
    notes: int


class FateFinishedPayload(EventPayload):
    rejected: list[Any] = Field(default_factory=list)
    corrected: list[Any] = Field(default_factory=list)
    fate_debt: bool | None = None


class CouncilPayload(EventPayload):
    id: int | None = None
    topic: str
    passed: bool
    motion: str | None = None


class ChatPayload(EventPayload):
    son_id: int
    attitude: str
    change: int


class NewSonPayload(EventPayload):
    son_id: int
    name: str | None = None
    rarity: str | None = None


class SonAscendedPayload(EventPayload):
    son_id: int
    rarity: str


class RevelationPayload(EventPayload):
    entity_id: int | None = None
    record_id: int | None = None
    name: str | None = None


class WorldBornPayload(EventPayload):
    world_id: int
    name: str | None = None


class GenesisPayload(EventPayload):
    world_id: int | None = None


class EntityDeepenedPayload(EventPayload):
    entity_id: int
    name: str


class ForeignGodDeepenedPayload(EventPayload):
    id: int
    name: str


class EpicPayload(EventPayload):
    son_id: int | None = None
    creator: bool = False
    title: str


class NetworkRepairedPayload(EventPayload):
    kind: str | None = None
    type: str | None = None
    text: str


class TranslatedPayload(EventPayload):
    language_id: int
    new_words: int


class NotificationPayload(EventPayload):
    id: int
    category: str
    label: str
    severity: int
    title: str
    body: str | None = None
    target_node_id: int | None = None
    chronicle_id: int | None = None
    toast: bool = False


class ChangesPayload(EventPayload):
    version: str


class WorldReplacedPayload(EventPayload):
    message: str
    version: str


class LedgerUndonePayload(EventPayload):
    entry_id: int
    applied: int
    conflicts: int


class ImageQueuedPayload(EventPayload):
    node_id: int
    position: int


class ImageProgressPayload(EventPayload):
    node_id: int
    stage: str
    percent: int
    step: int | None = None


class ImageDonePayload(EventPayload):
    node_id: int
    image_id: int
    file: str
    cover: bool


class ImageFailedPayload(EventPayload):
    node_id: int
    error: str


class BulkLogPayload(EventPayload):
    level: str
    text: str | None = None
    line: str | None = None


PAYLOADS: dict[EventKind, type[EventPayload]] = {
    EventKind.JOB_QUEUED: JobPayload,
    EventKind.JOB_STARTED: JobPayload,
    EventKind.JOB_PROGRESS: JobProgressPayload,
    EventKind.JOB_FINISHED: JobFinishedPayload,
    EventKind.JOB_FAILED: JobFailedPayload,
    EventKind.JOB_CANCELLED: JobPayload,
    EventKind.WORLD_CHANGED: WorldChangedPayload,
    EventKind.RULES_CHANGED: RulesChangedPayload,
    EventKind.ENGINE_NOTE: EngineNotePayload,
    EventKind.ENGINE_PHASE: EnginePhasePayload,
    EventKind.SYSTEM_NOTE: TextPayload,
    EventKind.SYSTEM_ERROR: ErrorPayload,
    EventKind.AGENT_RETRY: RetryPayload,
    EventKind.EPOCH_STARTED: EpochStartedPayload,
    EventKind.EPOCH_RESUMED: EpochResumedPayload,
    EventKind.EPOCH_PROGRESS: EpochProgressPayload,
    EventKind.EPOCH_STOP_REQUESTED: EmptyPayload,
    EventKind.EPOCH_STOPPED: EpochStoppedPayload,
    EventKind.EPOCH_FINISHED: EpochFinishedPayload,
    EventKind.EPOCH_BACKUP: FilePayload,
    EventKind.SON_DISTRIBUTED: SonDistributedPayload,
    EventKind.SON_TURN_QUEUED: SonTurnQueuedPayload,
    EventKind.SON_TURN_STARTED: SonTurnStartedPayload,
    EventKind.SON_TURN_FINISHED: SonTurnFinishedPayload,
    EventKind.MORTALS_STARTED: MortalsStartedPayload,
    EventKind.MORTAL_TURN_STARTED: MortalTurnStartedPayload,
    EventKind.MORTAL_TURN_FINISHED: MortalTurnFinishedPayload,
    EventKind.ENGINE_STARTED: EmptyPayload,
    EventKind.ENGINE_FINISHED: EngineFinishedPayload,
    EventKind.FATE_STARTED: EmptyPayload,
    EventKind.FATE_STEP: TextPayload,
    EventKind.FATE_FINISHED: FateFinishedPayload,
    EventKind.COUNCIL_HELD: CouncilPayload,
    EventKind.SON_CHAT_REPLIED: ChatPayload,
    EventKind.NEW_SON: NewSonPayload,
    EventKind.SON_ASCENDED: SonAscendedPayload,
    EventKind.REVELATION: RevelationPayload,
    EventKind.WORLD_BORN: WorldBornPayload,
    EventKind.GENESIS_FINISHED: GenesisPayload,
    EventKind.ENTITY_DEEPENED: EntityDeepenedPayload,
    EventKind.FOREIGN_GOD_DEEPENED: ForeignGodDeepenedPayload,
    EventKind.EPIC_WRITTEN: EpicPayload,
    EventKind.NETWORK_REPAIRED: NetworkRepairedPayload,
    EventKind.TRANSLATED: TranslatedPayload,
    EventKind.NOTIFICATION_CREATED: NotificationPayload,
    EventKind.CHANGES_AVAILABLE: ChangesPayload,
    EventKind.WORLD_REPLACED: WorldReplacedPayload,
    EventKind.LEDGER_UNDONE: LedgerUndonePayload,
    EventKind.BACKUP_TAKEN: FilePayload,
    EventKind.IMAGE_QUEUED: ImageQueuedPayload,
    EventKind.IMAGE_PROGRESS: ImageProgressPayload,
    EventKind.IMAGE_DONE: ImageDonePayload,
    EventKind.IMAGE_FAILED: ImageFailedPayload,
    EventKind.IMAGE_STATUS: EmptyPayload,
    EventKind.IMAGE_BULK_LOG: BulkLogPayload,
    EventKind.BATCH_DEEPEN_LOG: BulkLogPayload,
}


def event_model_name(kind: EventKind) -> str:
    return "".join(part.capitalize() for part in kind.value.replace(".", "_").split("_")) + "Event"


def envelope(kind: EventKind) -> type[BaseModel]:
    literal: Any = Literal[kind.value]
    return create_model(
        event_model_name(kind),
        id=(int, ...),
        kind=(literal, ...),
        payload=(PAYLOADS.get(kind, EventPayload), ...),
        at=(datetime, ...),
    )


ENVELOPES: dict[EventKind, type[BaseModel]] = {kind: envelope(kind) for kind in EventKind}
SERVER_EVENT: Any = Annotated[reduce(operator.or_, ENVELOPES.values()), Field(discriminator="kind")]
