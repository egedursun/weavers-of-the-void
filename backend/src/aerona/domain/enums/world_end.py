from enum import StrEnum


class WorldEnd(StrEnum):
    SHATTERED = "shattered"
    SWALLOWED = "swallowed"
    FROZEN_DEAD = "frozen_dead"
    SUNK_INTO_VOID = "sunk_into_void"
    FORGOTTEN = "forgotten"
    TRANSFIGURED = "transfigured"


class WorldEndCause(StrEnum):
    IMPACT = "impact"
    DIVINE_WRATH = "divine_wrath"
    STAR_GIANT = "star_giant"
    STAR_DEATH = "star_death"
    VOID = "void"
    OBLIVION = "oblivion"
    BELIEF_DRIFT = "belief_drift"
