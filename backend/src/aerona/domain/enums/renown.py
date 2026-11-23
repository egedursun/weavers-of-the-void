from enum import StrEnum


class ReputationAxis(StrEnum):
    HEROISM = "heroism"
    HONOUR = "honour"
    CRUELTY = "cruelty"
    PIETY = "piety"
    GENEROSITY = "generosity"
    WISDOM = "wisdom"
    TRICKERY = "trickery"
    SKILL_RENOWN = "skill_renown"
    TROUBLEMAKER = "troublemaker"
    MERCY = "mercy"
    JUSTICE = "justice"


class Currency(StrEnum):
    PRESTIGE = "prestige"
    PIETY = "piety"
    DREAD = "dread"
    TYRANNY = "tyranny"


class ClaimKind(StrEnum):
    TRUE = "true"
    SHARED = "shared"
    FALSE = "false"
    INFLATED = "inflated"


class ClaimStatus(StrEnum):
    STANDING = "standing"
    VERIFIED = "verified"
    EXPOSED = "exposed"
    DISPUTED = "disputed"


class LorePrice(StrEnum):
    WEALTH = "wealth"
    FAVOUR = "favour"
    RENOWN = "renown"
    EXCHANGE = "exchange"
    SERVICE = "service"


class ServiceTask(StrEnum):
    QUEST = "quest"
    THEFT = "theft"
    KILLING = "killing"
    RITE = "rite"
