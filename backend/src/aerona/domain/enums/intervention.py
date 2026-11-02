from enum import StrEnum


class Disaster(StrEnum):
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    PLAGUE = "plague"
    DROUGHT = "drought"
    STORM = "storm"


class Miracle(StrEnum):
    HEALING = "healing"
    BOUNTY = "bounty"
    PEACE = "peace"
    PROTECTION = "protection"


class InterventionKind(StrEnum):
    MIRACLE = "miracle"
    DISASTER = "disaster"
    TEACH_KNOWLEDGE = "teach_knowledge"
    CURSE = "curse"
