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
    RELIABILITY = "reliability"
    HOSPITALITY = "hospitality"


class Currency(StrEnum):
    PRESTIGE = "prestige"
    PIETY = "piety"
    DREAD = "dread"
    TYRANNY = "tyranny"
    TRUST = "trust"
    LEARNING = "learning"


class ClaimKind(StrEnum):
    TRUE = "true"
    SHARED = "shared"
    FALSE = "false"
    INFLATED = "inflated"
    BORROWED = "borrowed"


class ClaimStatus(StrEnum):
    STANDING = "standing"
    VERIFIED = "verified"
    EXPOSED = "exposed"
    DISPUTED = "disputed"
    FORGOTTEN = "forgotten"


class LorePrice(StrEnum):
    WEALTH = "wealth"
    FAVOUR = "favour"
    RENOWN = "renown"
    EXCHANGE = "exchange"
    SERVICE = "service"
    OATH = "oath"


class ServiceTask(StrEnum):
    QUEST = "quest"
    THEFT = "theft"
    KILLING = "killing"
    RITE = "rite"
