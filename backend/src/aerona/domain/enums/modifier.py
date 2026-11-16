from enum import StrEnum


class ModifierOp(StrEnum):
    ADD = "add"
    MULTIPLY = "multiply"


class ModifierSource(StrEnum):
    INJURY = "injury"
    CONDITION = "condition"
    TRAIT = "trait"
    LAW = "law"
    TRADITION = "tradition"
    ARTWORK = "artwork"
    DOCTRINE = "doctrine"
    TREATY = "treaty"
    STRUCTURE = "structure"
    WONDER = "wonder"
    TERRAIN = "terrain"
    WEATHER = "weather"
    SEASON = "season"
    NATURAL_LAW = "natural_law"
    LAW_GRAMMAR = "law_grammar"
    GOD_POWER = "god_power"
    BLESSING = "blessing"
    PERK = "perk"
    CURSE = "curse"
    DOMINION = "dominion"
    PHENOMENON = "phenomenon"
    COSMOS = "cosmos"
    RIFT = "rift"
    GOD_DEATH = "god_death"
    PLAYER = "player"
    SUPPRESSION = "suppression"
    PIN = "pin"


class IncidentRole(StrEnum):
    SUBJECT = "subject"
    ACTOR = "actor"
    TARGET = "target"
    WITNESS = "witness"
    PLACE = "place"
