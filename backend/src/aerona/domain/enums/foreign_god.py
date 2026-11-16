from enum import StrEnum


class ForeignGodStatus(StrEnum):
    AWAKE = "awake"
    ASLEEP = "asleep"
    DEFEATED = "defeated"
    DEAD = "dead"


class ForeignGodPowerEffect(StrEnum):
    SHIELD = "shield"
    CALLER = "caller"
    THIEF = "thief"
    DESTROYER = "destroyer"
    FERTILE = "fertile"
    REVIVING = "reviving"
    DEATHLESS = "deathless"
    PERSUASION = "persuasion"


class PantheonStructure(StrEnum):
    COUNCIL = "council"
    FAMILY = "family"
    COURT = "court"
    RIVALS = "rivals"
    SINGLE_HIGH_GOD = "single_high_god"
    DUAL = "dual"
    LOOSE = "loose"


class PantheonTie(StrEnum):
    ELDER = "elder"
    YOUNGER = "younger"
    PARTNER = "partner"
    KIN = "kin"
    RULER_OF = "ruler_of"
    SERVANT_OF = "servant_of"
    RIVAL = "rival"
    ALLY = "ally"
