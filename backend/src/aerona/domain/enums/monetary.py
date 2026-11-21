from enum import StrEnum


class MonetaryAim(StrEnum):
    STABLE_VALUE = "stable_value"
    CHEAP_CREDIT = "cheap_credit"
    FUND_THE_STATE = "fund_the_state"
    PEG = "peg"
    GROWTH = "growth"
    NONE = "none"
