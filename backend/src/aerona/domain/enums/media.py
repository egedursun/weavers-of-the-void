from enum import StrEnum


class RecordForm(StrEnum):
    WRITTEN = "written"
    PRINTED = "printed"
    IMAGE = "image"
    SOUND = "sound"
    MOVING_IMAGE = "moving_image"
    SIGNAL = "signal"
    NETWORK = "network"
    LIVING = "living"
    CRAFTED = "crafted"
    MENTAL = "mental"
    SCENT = "scent"
    TACTILE = "tactile"


class MediaItemKind(StrEnum):
    NEWS = "news"
    OPINION = "opinion"
    RECORD_OF_EVENT = "record_of_event"
    ENTERTAINMENT = "entertainment"
    INSTRUCTION = "instruction"
    PROMOTION = "promotion"
    DEVOTION = "devotion"
    OFFICIAL = "official"
    SATIRE = "satire"
    SPORT = "sport"
    NOTICES = "notices"


class OutletFunding(StrEnum):
    SALES = "sales"
    PATRONAGE = "patronage"
    ADVERTISING = "advertising"
    STATE = "state"


class CensorMeasure(StrEnum):
    CENSOR = "censor"
    LICENSE = "license"
    SEIZE = "seize"
    CLOSE = "close"
