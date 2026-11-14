from enum import StrEnum


class FormationZone(StrEnum):
    INNER = "inner"
    SNOW_LINE = "snow_line"
    OUTER = "outer"


class GiantMigration(StrEnum):
    NONE = "none"
    INWARD = "inward"
    OUTWARD = "outward"


class SeasonCause(StrEnum):
    ORBIT = "orbit"
    NATURAL_LAW = "natural_law"
    DIVINE = "divine"


class SeasonSpell(StrEnum):
    SUMMER = "summer"
    WINTER = "winter"


class AgeCycle(StrEnum):
    LINEAR = "linear"
    CYCLIC = "cyclic"


class ArcTemplate(StrEnum):
    RISE_AND_FALL = "rise_and_fall"
    RAGS_TO_RICHES = "rags_to_riches"
    REVENGE = "revenge"
    REDEMPTION = "redemption"
    QUEST = "quest"
    TRAGEDY = "tragedy"
    FORBIDDEN_LOVE = "forbidden_love"
    RIVALRY = "rivalry"
    MENTOR_AND_HEIR = "mentor_and_heir"
    EXILE_AND_RETURN = "exile_and_return"
    CORRUPTION = "corruption"
    COMING_OF_AGE = "coming_of_age"
    FALL_OF_A_HOUSE = "fall_of_a_house"
    FOUNDING = "founding"
    APOTHEOSIS = "apotheosis"


class ArcStage(StrEnum):
    INCITING = "inciting"
    RISING = "rising"
    CRISIS = "crisis"
    CLIMAX = "climax"
    CALL = "call"
    REFUSAL = "refusal"
    MENTOR = "mentor"
    THRESHOLD = "threshold"
    ORDEAL = "ordeal"
    RETURN = "return"
    RESOLUTION = "resolution"


class ArcOutcome(StrEnum):
    OPEN = "open"
    FULFILLED = "fulfilled"
    FAILED = "failed"
    TWISTED = "twisted"
    IRONIC = "ironic"


class ArcRole(StrEnum):
    RIVAL = "rival"
    MENTOR = "mentor"
    BELOVED = "beloved"
    BETRAYER = "betrayer"
    HEIR = "heir"
    FOE = "foe"
    ALLY = "ally"


class SetupKind(StrEnum):
    PROPHECY = "prophecy"
    OMEN = "omen"
    DREAM = "dream"
    FORESIGHT = "foresight"
    THREAD = "thread"
    PORTENT = "portent"


class PayoffKind(StrEnum):
    OPEN = "open"
    FULFILLED = "fulfilled"
    SUBVERTED = "subverted"
    LAPSED = "lapsed"
