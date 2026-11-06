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


class Currency(StrEnum):
    PRESTIGE = "prestige"
    PIETY = "piety"
    DREAD = "dread"
    TYRANNY = "tyranny"


class ClaimKind(StrEnum):
    TRUE = "true"
    SHARED = "shared"
    FALSE = "false"


class ClaimStatus(StrEnum):
    STANDING = "standing"
    VERIFIED = "verified"
    EXPOSED = "exposed"


class LoreKind(StrEnum):
    TECHNIQUE = "technique"
    SITE = "site"
    MAP = "map"
    PROPHECY = "prophecy"


class LorePrice(StrEnum):
    WEALTH = "wealth"
    FAVOUR = "favour"
    RENOWN = "renown"
