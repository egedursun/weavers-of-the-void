from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import CosmosRecord, CreatorRecord, EntityRecord, EpochRecord, SonPublic, ThreadRecord
from aerona.domain.enums.creator import CreatorMoodLabel
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.records import EpochStatsData
from aerona.services.discovery import GuestWorld
from aerona.services.images.queue import QueueStatus


class SonRelationItem(ApiModel):
    son_a_id: int
    son_b_id: int
    value: int
    note: str | None


class WorldBriefItem(ApiModel):
    id: int
    name: str
    world_type: str
    discovery: str
    leakage: int


class Covenant(ApiModel):
    son_a_id: int
    son_b_id: int
    description: str | None


class RunningJob(ApiModel):
    group: str
    job_id: str


class HalfEpochState(ApiModel):
    epoch: int
    phase: int
    started: bool


class MoodSummary(ApiModel):
    contentment: int
    anger: int
    interest: int
    loneliness: int
    label: CreatorMoodLabel


class BulkSummary(ApiModel):
    running: bool
    stop_requested: bool
    total: int
    done: int
    failed: int
    skipped: int


class StateResponse(ApiModel):
    world: CosmosRecord | None
    creator: CreatorRecord | None
    creator_cover: str | None
    world_cover: str | None
    sons: list[SonPublic]
    counts: dict[EntityType, int]
    prayers_pending: int
    relations: list[SonRelationItem]
    worlds: list[WorldBriefItem]
    foreign_god_count: int
    pending_son_ids: list[int]
    covenants: list[Covenant]
    threads: list[ThreadRecord]
    last_epoch: EpochRecord | None
    image_count: int
    promptless_count: int
    pulse: EpochStatsData | None
    read_only: bool
    discovery: GuestWorld | None
    version: str
    notifications_unread: int
    running_jobs: int
    epoch_running: bool
    half_epoch: HalfEpochState | None
    mood: MoodSummary | None
    image_gen: QueueStatus
    batch_deepen: BulkSummary
    llm_enabled: bool


class ChangesResponse(ApiModel):
    full: bool
    version: str
    entities: list[EntityRecord]
    removed_entity_ids: list[int]
    sons: list[SonPublic]
    removed_son_ids: list[int]
    new_chronicle_lines: int
    bonds_changed: bool
    cosmos_changed: bool
    worlds_changed: bool
    relations_changed: bool
    foreign_god_ids: list[int]
