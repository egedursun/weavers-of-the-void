from enum import StrEnum


class EventKind(StrEnum):
    JOB_QUEUED = "job.queued"
    JOB_STARTED = "job.started"
    JOB_PROGRESS = "job.progress"
    JOB_FINISHED = "job.finished"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"
    WORLD_CHANGED = "world.changed"
    RULES_CHANGED = "rules.changed"
    ENGINE_NOTE = "engine.note"
    ENGINE_PHASE = "engine.phase"
    SYSTEM_NOTE = "system.note"
    SYSTEM_ERROR = "system.error"
    AGENT_RETRY = "agent.retry"
    EPOCH_STARTED = "epoch.started"
    EPOCH_RESUMED = "epoch.resumed"
    EPOCH_PROGRESS = "epoch.progress"
    EPOCH_STOP_REQUESTED = "epoch.stop_requested"
    EPOCH_STOPPED = "epoch.stopped"
    EPOCH_FINISHED = "epoch.finished"
    EPOCH_BACKUP = "epoch.backup"
    SON_DISTRIBUTED = "son.distributed"
    SON_TURN_QUEUED = "son.turn_queued"
    SON_TURN_STARTED = "son.turn_started"
    SON_TURN_FINISHED = "son.turn_finished"
    MORTALS_STARTED = "mortals.started"
    MORTAL_TURN_STARTED = "mortal.turn_started"
    MORTAL_TURN_FINISHED = "mortal.turn_finished"
    ENGINE_STARTED = "engine.started"
    ENGINE_FINISHED = "engine.finished"
    FATE_STARTED = "fate.started"
    FATE_STEP = "fate.step"
    FATE_FINISHED = "fate.finished"
    COUNCIL_HELD = "council.held"
    SON_CHAT_REPLIED = "son.chat_replied"
    NEW_SON = "son.new"
    SON_ASCENDED = "son.ascended"
    REVELATION = "creator.revelation"
    WORLD_BORN = "world.born"
    GENESIS_FINISHED = "genesis.finished"
    ENTITY_DEEPENED = "entity.deepened"
    FOREIGN_GOD_DEEPENED = "foreign_god.deepened"
    EPIC_WRITTEN = "epic.written"
    NETWORK_REPAIRED = "network.repaired"
    TRANSLATED = "language.translated"
    NOTIFICATION_CREATED = "notification.created"
    CHANGES_AVAILABLE = "world.changes"
    WORLD_REPLACED = "world.replaced"
    LEDGER_UNDONE = "ledger.undone"
    BACKUP_TAKEN = "backup.taken"
    IMAGE_QUEUED = "image.queued"
    IMAGE_PROGRESS = "image.progress"
    IMAGE_DONE = "image.done"
    IMAGE_FAILED = "image.failed"
    IMAGE_STATUS = "image.status"
    IMAGE_BULK_LOG = "image.bulk_log"
    BATCH_DEEPEN_LOG = "batch_deepen.log"
    STREAM_HELLO = "stream.hello"
    AGENT_STREAM = "agent.stream"
    AGENT_THOUGHT = "agent.thought"
    AGENT_TOOL_PREPARING = "agent.tool_preparing"
    AGENT_TOOL_WRITING = "agent.tool_writing"
    AGENT_TOOL_CALLED = "agent.tool_called"
    AGENT_TOOL_RESULT = "agent.tool_result"
    AGENT_WRITING = "agent.writing"
    DIVINE_WILL_CYCLE_STARTED = "divine_will.cycle_started"
    DIVINE_WILL_CYCLE_FINISHED = "divine_will.cycle_finished"
    DIVINE_WILL_CONFIRMATION_REQUESTED = "divine_will.confirmation_requested"
    DIVINE_WILL_ARTIFACT_CHANGED = "divine_will.artifact_changed"
    DIVINE_WILL_PLAN_CHANGED = "divine_will.plan_changed"
    DIVINE_WILL_FORECAST_PROGRESS = "divine_will.forecast_progress"
    DIVINE_WILL_INDEX_PROGRESS = "divine_will.index_progress"


TRANSIENT_KINDS = frozenset(
    {
        EventKind.AGENT_STREAM,
        EventKind.AGENT_TOOL_PREPARING,
        EventKind.AGENT_TOOL_WRITING,
        EventKind.AGENT_WRITING,
    }
)

EPOCH_TRACKING_KINDS = frozenset({EventKind.EPOCH_STARTED, EventKind.EPOCH_RESUMED, EventKind.EPOCH_PROGRESS, EventKind.EPOCH_FINISHED})

UNSTORED_KINDS = TRANSIENT_KINDS | frozenset({EventKind.JOB_PROGRESS, EventKind.IMAGE_PROGRESS, EventKind.CHANGES_AVAILABLE, EventKind.STREAM_HELLO})
