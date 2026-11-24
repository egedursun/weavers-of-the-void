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
    ANIMAL_SIGNS = "animal_signs"
    DREAM = "dream"


class WeatherWorkMethod(StrEnum):
    RITE = "rite"
    POWER = "power"
    SEEDING = "seeding"
    DIVERSION = "diversion"
    MADE_STRUCTURE = "made_structure"
    LIVING_CRAFT = "living_craft"
    BARGAIN = "bargain"
    MADE_MIND = "made_mind"


class WeatherAim(StrEnum):
    RAIN = "rain"
    DRY = "dry"
    CALM = "calm"
    COLD = "cold"
    WARM = "warm"
    WIND = "wind"
    SNOW = "snow"
