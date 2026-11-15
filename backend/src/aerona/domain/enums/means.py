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


class LockKind(StrEnum):
    BAR = "bar"
    WARDED = "warded"
    TUMBLER = "tumbler"
    COMBINATION = "combination"
    WARDED_SEAL = "warded_seal"


class WaterLift(StrEnum):
    SHADUF = "shaduf"
    NORIA = "noria"
    SCREW = "screw"
    CHAIN_PUMP = "chain_pump"
    STEAM_PUMP = "steam_pump"


class NavigationAid(StrEnum):
    COMPASS = "compass"
    ASTROLABE = "astrolabe"
    LOG_LINE = "log_line"
    CHARTS = "charts"


class ContainerKind(StrEnum):
    AMPHORA = "amphora"
    BARREL = "barrel"
    SACK = "sack"
    CRATE = "crate"
    JAR = "jar"
    CHEST = "chest"
