from enum import StrEnum


class SavingForm(StrEnum):
    HOARD = "hoard"
    DEPOSIT = "deposit"
    INVESTMENT = "investment"
    LAND = "land"
    GOODS = "goods"


class HoardState(StrEnum):
    HIDDEN = "hidden"
    LOST = "lost"
    FOUND = "found"
    SPENT = "spent"


class OwnershipRegime(StrEnum):
    HOUSEHOLD = "household"
    KIN_GROUP = "kin_group"
    COMMUNITY = "community"
    TEMPLE = "temple"
    RULER = "ruler"
    STATE = "state"
    PRIVATE = "private"
    COOPERATIVE = "cooperative"
    COMPANY = "company"
    COMMON = "common"
    NONE = "none"


class AllocationMode(StrEnum):
    MARKET = "market"
    REDISTRIBUTION = "redistribution"
    COMMAND = "command"
    OBLIGATION = "obligation"
    GIFT = "gift"
    NEED = "need"
    ABUNDANCE = "abundance"


class OrderLabour(StrEnum):
    FREE = "free"
    KIN = "kin"
    CORVEE = "corvee"
    SERF = "serf"
    BOUND = "bound"
    ENSLAVED = "enslaved"
    CONSCRIPTED = "conscripted"
    COOPERATIVE = "cooperative"
    MADE = "made"


class DistributionRule(StrEnum):
    BY_HOLDING = "by_holding"
    BY_OFFICE = "by_office"
    BY_NEED = "by_need"
    BY_WORK = "by_work"
    BY_SHARE = "by_share"
    EQUAL = "equal"
    BY_PRESTIGE = "by_prestige"


class TransitionKind(StrEnum):
    COLLECTIVISATION = "collectivisation"
    NATIONALISATION = "nationalisation"
    PRIVATISATION = "privatisation"
    LAND_REFORM = "land_reform"
    ENCLOSURE = "enclosure"
    EMANCIPATION = "emancipation"
    DECOLLECTIVISATION = "decollectivisation"
    RESTORATION_OF_HOLDINGS = "restoration_of_holdings"


class TransitionStage(StrEnum):
    PROCLAIMED = "proclaimed"
    TRANSFERRING = "transferring"
    DONE = "done"
    FAILED = "failed"


class Compensation(StrEnum):
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"


class TouristSight(StrEnum):
    WONDER = "wonder"
    BATHS = "baths"
    SACRED = "sacred"
    BATTLEFIELD = "battlefield"
    CITY = "city"
    COLLECTION = "collection"
    GARDEN = "garden"
