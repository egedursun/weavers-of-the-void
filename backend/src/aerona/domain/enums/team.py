from enum import StrEnum


class QueuedActStatus(StrEnum):
    QUEUED = "queued"
    APPLIED = "applied"
    PROPOSED = "proposed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueuedActSource(StrEnum):
    LEVER = "lever"
    UNDO = "undo"
    RULES = "rules"
    DIVINE_WILL = "divine_will"
    PRESENCE = "presence"


class ProposalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class CanonTouch(StrEnum):
    HELD_THING = "held_thing"
    CANON_STATUS = "canon_status"
    CANON_FACT = "canon_fact"
    HOLD_CHANGED = "hold_changed"
    LOCK_CHANGED = "lock_changed"
    LOCKED_FIELD = "locked_field"
