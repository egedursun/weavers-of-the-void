from enum import StrEnum


class WritingMedium(StrEnum):
    CLAY_TABLET = "clay_tablet"
    WAX_TABLET = "wax_tablet"
    BARK = "bark"
    PALM_LEAF = "palm_leaf"
    PAPYRUS = "papyrus"
    PARCHMENT = "parchment"
    PAPER = "paper"
    METAL_PLATE = "metal_plate"
    STONE = "stone"
    KNOTTED_CORD = "knotted_cord"
    CALCIFIED_TISSUE = "calcified_tissue"
    SILK = "silk"
    WOOD_SLIPS = "wood_slips"
    ELECTRONIC = "electronic"


class LockKind(StrEnum):
    BAR = "bar"
    WARDED = "warded"
    TUMBLER = "tumbler"
    COMBINATION = "combination"
    WARDED_SEAL = "warded_seal"
    WORKED = "worked"
    ELECTRONIC = "electronic"


class WaterLift(StrEnum):
    SHADUF = "shaduf"
    NORIA = "noria"
    SCREW = "screw"
    CHAIN_PUMP = "chain_pump"
    STEAM_PUMP = "steam_pump"
    WIND_PUMP = "wind_pump"
    ELECTRIC_PUMP = "electric_pump"


class NavigationAid(StrEnum):
    COMPASS = "compass"
    ASTROLABE = "astrolabe"
    LOG_LINE = "log_line"
    CHARTS = "charts"
    SOUNDING_LINE = "sounding_line"
    WAYFINDING = "wayfinding"
    BEACONS = "beacons"
    POSITIONING = "positioning"


class ContainerKind(StrEnum):
    AMPHORA = "amphora"
    BARREL = "barrel"
    SACK = "sack"
    CRATE = "crate"
    JAR = "jar"
    CHEST = "chest"
    BALE = "bale"
    BASKET = "basket"
    SKIN = "skin"
    TANK = "tank"
