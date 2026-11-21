from enum import StrEnum


class DivineCount(StrEnum):
    ONE = "one"
    ONE_ABOVE_MANY = "one_above_many"
    MANY = "many"
    PAIRS = "pairs"
    ALL_IS_DIVINE = "all_is_divine"
    NONE = "none"


class DivineNearness(StrEnum):
    DISTANT = "distant"
    PRESENT = "present"
    WITHIN = "within"


class DivinePersonhood(StrEnum):
    PERSONS = "persons"
    FORCES = "forces"
    PRINCIPLE = "principle"
    MIXED = "mixed"


class CreatorPlace(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    UNKNOWN = "unknown"
    DENIED = "denied"
    RIVAL = "rival"


class GodReading(StrEnum):
    TRUE = "true"
    SERVANT = "servant"
    DEMON = "demon"
    UNKNOWN = "unknown"


class ConceptionAxis(StrEnum):
    COUNT = "count"
    NEARNESS = "nearness"
    PERSONHOOD = "personhood"
    CREATOR = "creator"
