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
    GRANT = "grant"
    BLESS = "bless"
    CREATE = "create"
    DESTROY = "destroy"
    SHAPE = "shape"
    REVEAL = "reveal"
    CONCEAL = "conceal"
    SUMMON = "summon"
    BIND = "bind"
    FREE = "free"
    HEAL = "heal"
    HARM = "harm"
    RAISE = "raise"
    INSPIRE = "inspire"
    TERRIFY = "terrify"
    PROTECT = "protect"
    GUIDE = "guide"
    JUDGE = "judge"
    TRANSFORM = "transform"
    FORESEE = "foresee"
    HASTEN = "hasten"
    SLOW = "slow"
    MULTIPLY = "multiply"
    STILL = "still"
    WAKE = "wake"
    REMEMBER = "remember"
    ERASE = "erase"
