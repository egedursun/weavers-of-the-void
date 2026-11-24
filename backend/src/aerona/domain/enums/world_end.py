from enum import StrEnum


class WorldEnd(StrEnum):
    SHATTERED = "shattered"
    CONSUMED = "consumed"
    FROZEN_DEAD = "frozen_dead"
    SUNK_INTO_VOID = "sunk_into_void"
    FORGOTTEN = "forgotten"
    TRANSFIGURED = "transfigured"
    DROWNED = "drowned"
    BURNED = "burned"
    DEVOURED = "devoured"
    EMPTIED = "emptied"
    MERGED = "merged"


class WorldEndCause(StrEnum):
    IMPACT = "impact"
    DIVINE_WRATH = "divine_wrath"
    STAR_GIANT = "star_giant"
    STAR_DEATH = "star_death"
    VOID = "void"
    OBLIVION = "oblivion"
    BELIEF_DRIFT = "belief_drift"
    RUNAWAY_CLIMATE = "runaway_climate"
    WAR = "war"
    OUTER_HUNGER = "outer_hunger"
    PLAGUE = "plague"
    RUNAWAY_MAKING = "runaway_making"
    STRUCTURE_FAILURE = "structure_failure"
