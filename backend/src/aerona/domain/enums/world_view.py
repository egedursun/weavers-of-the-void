from enum import StrEnum


class WorldLight(StrEnum):
    STAR = "star"
    LAVA_GLOW = "lava_glow"
    MAGIC = "magic"
    INNER_SUN = "inner_sun"
    DIVINE = "divine"
    SHIP_CYCLE = "ship_cycle"
    FADING_GOD = "fading_god"
    NONE = "none"


class SettleMode(StrEnum):
    GROUND = "ground"
    FLOATING = "floating"
    STILT = "stilt"
    OASIS = "oasis"
    VENT = "vent"
    HABITAT = "habitat"
    BAND = "band"
    DECK = "deck"


class WarTerrain(StrEnum):
    LAND = "land"
    NAVAL = "naval"
    SKY = "sky"
    BOARDING = "boarding"
    STRATA = "strata"


class BindingNeed(StrEnum):
    NONE = "none"
    WATER = "water"
    HEAT = "heat"
    AIR = "air"
    OFFERINGS = "offerings"
    BELIEF = "belief"
