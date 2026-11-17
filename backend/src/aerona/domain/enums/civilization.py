from enum import StrEnum


class TierCapability(StrEnum):
    EXPEDITION = "expedition"
    COLONY = "colony"
    CONQUEST = "conquest"
    ROUTE_SEARCH = "route_search"
    SHIPBUILDING = "shipbuilding"
    INTERWORLD_TREATY = "interworld_treaty"
    FEDERATION = "federation"
    LOAN = "loan"
    EXPLORATION = "exploration"
    DEPOSIT_CLAIM = "deposit_claim"


class DebtTiming(StrEnum):
    ON_TIME = "on_time"
    OVERDUE = "overdue"


class IndependenceAnswer(StrEnum):
    WAR = "war"
    RELEASED = "released"
