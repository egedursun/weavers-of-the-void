from enum import StrEnum


class HouseDuty(StrEnum):
    FOOD = "food"
    WATER = "water"
    FUEL = "fuel"
    CLEANING = "cleaning"
    TEXTILES = "textiles"
    CHILDCARE = "childcare"
    ELDERCARE = "eldercare"
    ANIMALS = "animals"
    REPAIRS = "repairs"
    SICKCARE = "sickcare"
    HOUSEHOLD_RITES = "household_rites"
    TEACHING = "teaching"
    ACCOUNTS = "accounts"


class LeisureKind(StrEnum):
    CONVERSATION = "conversation"
    GAMES = "games"
    SPORT = "sport"
    MUSIC = "music"
    CRAFTS = "crafts"
    COLLECTING = "collecting"
    READING = "reading"
    EXCURSION = "excursion"
    TOURISM = "tourism"
    DRINKING = "drinking"
    WORSHIP_EXTRA = "worship_extra"
    REST = "rest"
    MEDIA = "media"
    DANCE = "dance"
    STORYTELLING = "storytelling"
    HUNTING = "hunting"
    GARDENING = "gardening"
    BATHING = "bathing"
    ANIMAL_KEEPING = "animal_keeping"


class WashFrequency(StrEnum):
    NONE = "none"
    BY_RITE = "by_rite"
    SEASONAL = "seasonal"
    WEEKLY = "weekly"
    DAILY = "daily"


class WashPlace(StrEnum):
    HOME = "home"
    BATH_HOUSE = "bath_house"
    RIVER = "river"
    RITE = "rite"


class WasteHandling(StrEnum):
    NONE = "none"
    PITS = "pits"
    CARRIED_OUT = "carried_out"
    SEWERS = "sewers"
    BURNED = "burned"
    COMPOSTED = "composted"


class DistanceNorm(StrEnum):
    CLOSE = "close"
    ARM = "arm"
    WIDE = "wide"


class TouchNorm(StrEnum):
    OPEN = "open"
    KIN_ONLY = "kin_only"
    SPARING = "sparing"
    FORBIDDEN = "forbidden"


class PostureForm(StrEnum):
    STAND = "stand"
    SIT_FLOOR = "sit_floor"
    SIT_RAISED = "sit_raised"
    KNEEL = "kneel"
    RECLINE = "recline"


class ServiceTerms(StrEnum):
    WAGE = "wage"
    BOARD = "board"
    BOUND = "bound"


class ServiceEnd(StrEnum):
    UNPAID = "unpaid"
    DISMISSED = "dismissed"
    CHOSE = "chose"


class NormKind(StrEnum):
    DISTANCE = "distance"
    TOUCH = "touch"
    POSTURE = "posture"
    CLEANLINESS = "cleanliness"
