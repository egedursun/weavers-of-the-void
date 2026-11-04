from enum import StrEnum


class Disaster(StrEnum):
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    PLAGUE = "plague"
    DROUGHT = "drought"
    STORM = "storm"
    ERUPTION = "eruption"
    VOLCANIC_QUAKE = "volcanic_quake"


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
