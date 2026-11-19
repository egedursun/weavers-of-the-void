from enum import StrEnum


class ObservationMethod(StrEnum):
    SIGHT = "sight"
    LORE = "lore"
    ALMANAC = "almanac"
    INSTRUMENT = "instrument"
    NETWORK_OF_OBSERVERS = "network_of_observers"
    MODEL = "model"
    NETWORK = "network"
    POWER = "power"
    DIVINATION = "divination"


class WeatherWorkMethod(StrEnum):
    RITE = "rite"
    POWER = "power"
    SEEDING = "seeding"
    DIVERSION = "diversion"
    MADE_STRUCTURE = "made_structure"
    LIVING_CRAFT = "living_craft"


class WeatherAim(StrEnum):
    RAIN = "rain"
    DRY = "dry"
    CALM = "calm"
    COLD = "cold"
    WARM = "warm"
