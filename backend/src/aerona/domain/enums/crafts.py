from enum import StrEnum


class CatchGround(StrEnum):
    FISHERY = "fishery"
    TRAPPING = "trapping"
    FOWLING = "fowling"
    MARINE_HUNT = "marine_hunt"


class Gear(StrEnum):
    LINES = "lines"
    NETS = "nets"
    WEIRS = "weirs"
    TRAPS = "traps"
    SNARES = "snares"
    HARPOONS = "harpoons"


class CatchRight(StrEnum):
    COMMONS = "commons"
    OWNED = "owned"


class ChemicalProduct(StrEnum):
    DYE = "dye"
    SOAP = "soap"
    MORDANT = "mordant"
    TANNING = "tanning"
    FERTILISER = "fertiliser"
    MEDICINE = "medicine"
    INCENDIARY = "incendiary"
    EXPLOSIVE = "explosive"


class InsuranceCover(StrEnum):
    CARGO = "cargo"
    HOUSE = "house"
    LIFE = "life"


class RightKind(StrEnum):
    SONG = "song"
    DANCE = "dance"
    STORY = "story"
    RITE = "rite"
    DESIGN = "design"
    NAME = "name"
    TITLE = "title"
    TRADEMARK = "trademark"
    MARKET_PRIVILEGE = "market_privilege"


class RightAcquired(StrEnum):
    CREATED = "created"
    INHERITED = "inherited"
    BOUGHT = "bought"
    LICENSED = "licensed"
    STOLEN = "stolen"
    GRANTED = "granted"


class AssistiveAid(StrEnum):
    SPECTACLES = "spectacles"
    MAGNIFIER = "magnifier"
    TELESCOPE = "telescope"
    HEARING_HORN = "hearing_horn"
    CANE = "cane"


class ClockKind(StrEnum):
    SUNDIAL = "sundial"
    WATER_CLOCK = "water_clock"
    SAND_GLASS = "sand_glass"
    CANDLE_CLOCK = "candle_clock"
    MECHANICAL = "mechanical"
    ASTRONOMICAL = "astronomical"


class Notation(StrEnum):
    ADDITIVE = "additive"
    POSITIONAL = "positional"


class NumberMilestone(StrEnum):
    ZERO = "zero"
    PLACE_VALUE = "place_value"


class AffinityMode(StrEnum):
    CONSUMED = "consumed"
    WORN = "worn"
    INSCRIBED = "inscribed"
    GROUND = "ground"


class LinkToken(StrEnum):
    HAIR = "hair"
    BLOOD = "blood"
    NAME = "name"
    PORTRAIT = "portrait"
    FRAGMENT = "fragment"
