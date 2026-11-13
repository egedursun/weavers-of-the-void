from enum import StrEnum


class Criticality(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class SectionHazard(StrEnum):
    NONE = "none"
    FIRE = "fire"
    EXPLOSION = "explosion"
    FLOODING = "flooding"
    BREACH = "breach"
    CRASH = "crash"
    PANIC = "panic"
    COLLAPSE = "collapse"


class SectionState(StrEnum):
    SOUND = "sound"
    DAMAGED = "damaged"
    DISABLED = "disabled"
    DESTROYED = "destroyed"


class HarmForce(StrEnum):
    SIEGE = "siege"
    QUAKE = "quake"
    FIRE = "fire"
    FLOOD = "flood"
    STORM = "storm"
    WAR = "war"
    DECAY = "decay"
    DIVINE = "divine"
    SABOTAGE = "sabotage"
    IMPACT = "impact"
