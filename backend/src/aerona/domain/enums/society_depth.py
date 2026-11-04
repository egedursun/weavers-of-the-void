from enum import StrEnum


class ShortfallEffect(StrEnum):
    HUNGER = "hunger"
    HERDS = "herds"
    COLD = "cold"
    SICKNESS = "sickness"
    IMPIETY = "impiety"
    STATUS = "status"
    TOIL = "toil"
    INSECURITY = "insecurity"
    ARCANE = "arcane"


class LabourReason(StrEnum):
    CLASS = "class"
    PRICE = "price"
    STRUCTURE = "structure"
    RESOURCE = "resource"
    NO_STRUCTURE = "no_structure"
    CORVEE = "corvee"
    HELD = "held"


class DriftCause(StrEnum):
    GOD = "god"
    RULER = "ruler"
    NEIGHBOURS = "neighbours"
    IDEOLOGY = "ideology"
    WAR_FOUGHT = "war_fought"
    WAR_WON = "war_won"
    WAR_LOST = "war_lost"
    PLAGUE = "plague"
    FAMINE = "famine"
    TRADE = "trade"
    CONQUEST = "conquest"


class LoyaltyPart(StrEnum):
    TRIBUTE = "tribute"
    WEARINESS = "weariness"
    CONQUEST = "conquest"
    TAX = "tax"
    ROUTES = "routes"
    VICTORIES = "victories"
    FAITH = "faith"
    PROSPERITY = "prosperity"


GRIEVANCE_PARTS = frozenset({LoyaltyPart.TRIBUTE, LoyaltyPart.WEARINESS, LoyaltyPart.CONQUEST, LoyaltyPart.TAX})


class MobilityEvent(StrEnum):
    ENNOBLED = "ennobled"
    ENSLAVED = "enslaved"
    FREED = "freed"
    RUINED = "ruined"
