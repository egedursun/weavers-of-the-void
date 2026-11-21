from enum import StrEnum


class InterpretationFault(StrEnum):
    NONE = "none"
    LOST_MEANING = "lost_meaning"
    WRONG_TERM = "wrong_term"
    SOFTENED = "softened"
    HARDENED = "hardened"
    SLANTED = "slanted"
    INVENTED = "invented"


class InterpretedEvent(StrEnum):
    PARLEY = "parley"
    TREATY = "treaty"
    TRIAL = "trial"
    TRADE = "trade"
    SERMON = "sermon"
