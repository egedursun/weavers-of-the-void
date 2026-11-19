from enum import StrEnum


class FolkDomain(StrEnum):
    WEATHER = "weather"
    SKY = "sky"
    MATTER = "matter"
    LAND = "land"
    WATERS = "waters"
    PLANTS = "plants"
    ANIMALS = "animals"
    BODY = "body"
    ILLNESS = "illness"
    MIND = "mind"
    SOCIETY = "society"
    NUMBER = "number"
    TIME = "time"


class LoreHolders(StrEnum):
    ELDERS = "elders"
    SPECIALISTS = "specialists"
    EVERYONE = "everyone"


class LoreTransmission(StrEnum):
    ORAL = "oral"
    WRITTEN = "written"
    APPRENTICESHIP = "apprenticeship"
    RITE = "rite"


class FolkTaking(StrEnum):
    FOOD = "food"
    MEDICINE = "medicine"
    POISON = "poison"
    DANGER = "danger"
    HARMLESS = "harmless"
    CURSE = "curse"
    OMEN = "omen"
    SACRED = "sacred"


class NumberReading(StrEnum):
    LUCKY = "lucky"
    UNLUCKY = "unlucky"
    SACRED = "sacred"
    FORBIDDEN = "forbidden"
