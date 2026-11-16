from enum import StrEnum


class FortuneLaw(StrEnum):
    CAUSES_ONLY = "causes_only"
    PERSONAL = "personal"
    DIVINE = "divine"
    BELIEF_SHAPED = "belief_shaped"


class FortuneSourceKind(StrEnum):
    BLESSING = "blessing"
    CURSE = "curse"
    CHARM = "charm"
    DIVINE_FAVOUR = "divine_favour"
    DIVINE_DISFAVOUR = "divine_disfavour"
    FATE_POWER = "fate_power"
    NATURAL_LAW = "natural_law"
    OATH_KEPT = "oath_kept"
    OATH_BROKEN = "oath_broken"
    PLACE = "place"
    DAY = "day"
    PRICE_PAID = "price_paid"
    CARE = "care"
