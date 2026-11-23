from enum import StrEnum


class FossilSource(StrEnum):
    EXTINCT_SPECIES = "extinct_species"
    MEGAFAUNA = "megafauna"
    BEAST = "beast"
    PREVIOUS_CREATION = "previous_creation"
    EXTINCT_PEOPLE = "extinct_people"
    GOD = "god"
    BURIED_DEAD = "buried_dead"


class FossilReading(StrEnum):
    UNREAD = "unread"
    LEGEND = "legend"
    RELIC = "relic"
    DEEP_TIME = "deep_time"
    MATERIAL = "material"
    MEDICINE = "medicine"


class Preservation(StrEnum):
    ROCK = "rock"
    AMBER = "amber"
    ICE = "ice"
    BOG = "bog"
    TAR = "tar"
    ASH = "ash"
    DRY = "dry"
