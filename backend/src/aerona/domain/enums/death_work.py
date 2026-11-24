from enum import StrEnum


class DeathRole(StrEnum):
    WASHER = "washer"
    PREPARER = "preparer"
    KEEPER_OF_REMAINS = "keeper_of_remains"
    OFFICIANT = "officiant"
    MOURNER = "mourner"
    RECORD_KEEPER = "record_keeper"
    CARRIER = "carrier"
    GRAVE_MAKER = "grave_maker"


class DeathStanding(StrEnum):
    HONOURED = "honoured"
    PLAIN = "plain"
    AVOIDED = "avoided"


class RemainsTreatment(StrEnum):
    BURIAL = "burial"
    CREMATION = "cremation"
    EXPOSURE = "exposure"
    PRESERVATION = "preservation"
    WATER = "water"
    CONSUMPTION = "consumption"
    STORAGE = "storage"
    RETURN_TO_MAKER = "return_to_maker"
    RELEASE = "release"
    NONE_NEEDED = "none_needed"
