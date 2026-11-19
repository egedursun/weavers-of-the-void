from enum import StrEnum


class EndowmentPurpose(StrEnum):
    RELIEF = "relief"
    LEARNING = "learning"
    WORSHIP = "worship"
    HEALTH = "health"
    WORKS = "works"
    ART = "art"
    KIN = "kin"
    MEMORY = "memory"
    RESEARCH = "research"


class EndowmentCapital(StrEnum):
    LAND = "land"
    COIN = "coin"
    SHARES = "shares"
    RENTS = "rents"


class EndowmentTerms(StrEnum):
    PERPETUAL = "perpetual"
    FOR_A_TERM = "for_a_term"
    CONDITIONAL = "conditional"


class EndowmentState(StrEnum):
    SERVING = "serving"
    CAPTURED = "captured"
    CONFISCATED = "confiscated"
    ENDED = "ended"
