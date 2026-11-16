from enum import StrEnum


class OuterGoal(StrEnum):
    FEED = "feed"
    ENTER = "enter"
    BE_WORSHIPPED = "be_worshipped"
    UNMAKE_LAW = "unmake_law"
    GAIN_NAME = "gain_name"
    OPEN_RIFT = "open_rift"


class OuterPlanState(StrEnum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    THWARTED = "thwarted"


class IncursionStage(StrEnum):
    PROBING = "probing"
    BREACH = "breach"
    MANIFESTATION = "manifestation"
    RECEDING = "receding"


class OuterPrice(StrEnum):
    SANITY = "sanity"
    YEARS = "years"
    MEMORY = "memory"
    NAME = "name"
    SERVICE = "service"
    OFFERING = "offering"


class OuterRelation(StrEnum):
    RIVAL = "rival"
    IGNORE = "ignore"
    FEEDS_ON = "feeds_on"


class OuterSealKind(StrEnum):
    SEAL = "seal"
    BANISH = "banish"


class OuterFate(StrEnum):
    ACTIVE = "active"
    SEALED = "sealed"
    BANISHED = "banished"
    STARVED = "starved"
    DESTROYED = "destroyed"
