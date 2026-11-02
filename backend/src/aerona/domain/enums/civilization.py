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
