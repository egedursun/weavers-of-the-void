from enum import StrEnum


class DivineWillMode(StrEnum):
    COMMAND = "command"
    PLAN = "plan"
    ASK_LORE = "ask_lore"
    CREATIVE_WORK = "creative_work"
    MECHANICS_GUIDE = "mechanics_guide"
    FORESIGHT = "foresight"


class CycleStatus(StrEnum):
    RUNNING = "running"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CycleEventKind(StrEnum):
    PLAYER = "player"
    THOUGHT = "thought"
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    CONFIRMATION_REQUEST = "confirmation_request"
    CONFIRMATION_REPLY = "confirmation_reply"
    NOTICE = "notice"
    RETRY = "retry"
    ERROR = "error"


class CycleNotice(StrEnum):
    SUGGEST_MODE = "suggest_mode"
    VISION_UNAVAILABLE = "vision_unavailable"
    STEP_LIMIT = "step_limit"
    TRANSLATED = "translated"


class ConfirmationReason(StrEnum):
    DESTRUCTIVE = "destructive"
    COSTLY = "costly"
    BOTH = "both"


class ConfirmationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    EXPIRED = "expired"


class AttachmentKind(StrEnum):
    IMAGE = "image"
    DOCUMENT = "document"


class AttachmentStatus(StrEnum):
    STORED = "stored"
    CONVERTED = "converted"
    INDEXED = "indexed"
    UNREADABLE = "unreadable"


class ChunkSource(StrEnum):
    ENTITY = "entity"
    TYPED_SECTION = "typed_section"
    CHRONICLE = "chronicle"
    INCIDENT = "incident"
    SON = "son"
    FOREIGN_GOD = "foreign_god"
    WORLD = "world"
    STAR = "star"
    CREATOR = "creator"
    WORD = "word"
    EPOCH = "epoch"
    NOTE = "note"
    MESSAGE = "message"
    COUNCIL = "council"
    ARTIFACT = "artifact"
    ATTACHMENT = "attachment"


class ArtifactKind(StrEnum):
    STORY = "story"
    CHAPTER = "chapter"
    NOVEL = "novel"
    SCREENPLAY = "screenplay"
    POEM = "poem"
    CHRONICLE = "chronicle"
    ENCYCLOPEDIA = "encyclopedia"
    OUTLINE = "outline"
    NOTES = "notes"
    REPORT = "report"
    PLAN = "plan"
    FORECAST = "forecast"
    HTML_PAGE = "html_page"


class ArtifactFormat(StrEnum):
    MARKDOWN = "markdown"
    FOUNTAIN = "fountain"
    HTML = "html"


class ArtifactStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"


class ExportFormat(StrEnum):
    MD = "md"
    HTML = "html"
    PDF = "pdf"
    EPUB = "epub"
    DOCX = "docx"
    FOUNTAIN = "fountain"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"
    ABANDONED = "abandoned"


class StepImpact(StrEnum):
    SAFE = "safe"
    COSTLY = "costly"
    DESTRUCTIVE = "destructive"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"
    UNDONE = "undone"


class ForecastStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IndexStatus(StrEnum):
    FETCHING = "fetching"
    BUILDING = "building"
    WAITING = "waiting"
    READY = "ready"
    UNAVAILABLE = "unavailable"
