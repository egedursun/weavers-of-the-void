from enum import StrEnum


class FossilSource(StrEnum):
    EXTINCT_SPECIES = "extinct_species"
    MEGAFAUNA = "megafauna"
    BEAST = "beast"
    PREVIOUS_CREATION = "previous_creation"
    EXTINCT_PEOPLE = "extinct_people"


class FossilReading(StrEnum):
    UNREAD = "unread"
    LEGEND = "legend"
    RELIC = "relic"
    DEEP_TIME = "deep_time"
