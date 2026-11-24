from enum import StrEnum


class GarmentCategory(StrEnum):
    BODY_WRAP = "body_wrap"
    UPPER = "upper"
    LOWER = "lower"
    FULL_BODY = "full_body"
    OUTER_LAYER = "outer_layer"
    HEAD = "head"
    FACE_COVERING = "face_covering"
    FEET = "feet"
    HANDS = "hands"
    UNDERGARMENT = "undergarment"
    FASTENING = "fastening"
    ORNAMENT = "ornament"
    UNIFORM = "uniform"
    RITUAL_DRESS = "ritual_dress"
    WORK_PROTECTION = "work_protection"
    ENVIRONMENT_SUIT = "environment_suit"
    BODY_MARKING = "body_marking"
    SLEEPWEAR = "sleepwear"
    WATER_WEAR = "water_wear"
    CARRIER = "carrier"


class WearingRule(StrEnum):
    ANYONE = "anyone"
    BY_ROLE = "by_role"
    BY_CLASS = "by_class"
    BY_AGE = "by_age"
    BY_FAITH = "by_faith"
    BY_RANK = "by_rank"
    BY_GENDER_AS_THE_CULTURE_HOLDS = "by_gender_as_the_culture_holds"


class ColourFocus(StrEnum):
    DARK = "dark"
    LIGHT = "light"
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    BROWN = "brown"
    PURPLE = "purple"
    PINK = "pink"
    ORANGE = "orange"
    GREY = "grey"


class ColourMeaning(StrEnum):
    MOURNING = "mourning"
    RANK = "rank"
    SACRED = "sacred"
    DANGER = "danger"
    JOY = "joy"
    FACTION = "faction"
    NONE = "none"
    HEALTH = "health"
    PURITY = "purity"
    LIFE_STAGE = "life_stage"


class ScentUse(StrEnum):
    BURNED = "burned"
    WORN = "worn"
    ANOINTED = "anointed"
    HOUSEHOLD = "household"
    RITUAL = "ritual"
    MEDICINAL = "medicinal"
    SIGNAL = "signal"


class EmblemSystem(StrEnum):
    HERALDRY = "heraldry"
    SEAL = "seal"
    BANNER = "banner"
    TOTEM = "totem"
    BADGE = "badge"
    MONOGRAM = "monogram"
    MARK = "mark"
    GLYPH = "glyph"


class FurnishingCategory(StrEnum):
    SLEEPING = "sleeping"
    SEATING = "seating"
    STORAGE = "storage"
    TABLE = "table"
    LIGHTING = "lighting"
    HEATING = "heating"
    COOKING_VESSEL = "cooking_vessel"
    TABLEWARE = "tableware"
    HOUSEHOLD_TEXTILE = "household_textile"
    DECORATION = "decoration"
    SANITATION = "sanitation"
    SHRINE = "shrine"
    BATHING = "bathing"
    PLAY = "play"


class ToolCategory(StrEnum):
    CUTTING = "cutting"
    DIGGING = "digging"
    LIFTING = "lifting"
    MEASURING = "measuring"
    WRITING = "writing"
    FIRE_MAKING = "fire_making"
    CRAFTING = "crafting"
    MEDICAL = "medical"
    NAVIGATION = "navigation"
    COMPUTING = "computing"
    FARMING = "farming"
    FISHING = "fishing"
    HUNTING = "hunting"


class InstrumentCategory(StrEnum):
    STRING = "string"
    WIND = "wind"
    PERCUSSION = "percussion"
    VOICE = "voice"
    KEYBOARD = "keyboard"
    ELECTRONIC = "electronic"
    MADE = "made"
    LIVING = "living"
    WATER = "water"


class EnsembleRole(StrEnum):
    LEAD = "lead"
    ACCOMPANIMENT = "accompaniment"
    RHYTHM = "rhythm"
    DRONE = "drone"
    SOLO = "solo"


class MusicForm(StrEnum):
    SOLO = "solo"
    CHORUS = "chorus"
    ENSEMBLE = "ensemble"
    CALL_AND_RESPONSE = "call_and_response"
    LAYERED = "layered"
    IMPROVISED = "improvised"
    NOTATED = "notated"


class GameCategory(StrEnum):
    BOARD = "board"
    CHANCE = "chance"
    CARD = "card"
    BALL = "ball"
    RACING = "racing"
    COMBAT_SPORT = "combat_sport"
    ATHLETIC = "athletic"
    HUNTING_SPORT = "hunting_sport"
    WIT = "wit"
    TEAM = "team"
    SPECTACLE = "spectacle"
    GAMBLING = "gambling"
    NETWORK = "network"
    PUZZLE = "puzzle"
    ANIMAL_CONTEST = "animal_contest"


class SubstanceCategory(StrEnum):
    STIMULANT = "stimulant"
    DEPRESSANT = "depressant"
    HALLUCINOGEN = "hallucinogen"
    ANALGESIC = "analgesic"
    EUPHORIANT = "euphoriant"
    POWER_SUBSTANCE = "power_substance"
    MEDICINAL = "medicinal"
