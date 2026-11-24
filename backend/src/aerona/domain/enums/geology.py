from enum import StrEnum


class RockKind(StrEnum):
    SOIL = "soil"
    CLAY = "clay"
    SAND = "sand"
    LIMESTONE = "limestone"
    SANDSTONE = "sandstone"
    SHALE = "shale"
    GRANITE = "granite"
    BASALT = "basalt"
    MARBLE = "marble"
    OBSIDIAN = "obsidian"
    SLATE = "slate"
    CRYSTAL_BEDROCK = "crystal_bedrock"
    FROZEN_METHANE = "frozen_methane"
    BONE = "bone"
    GLASS = "glass"
    HALITE = "halite"
    COAL = "coal"
    CHALK = "chalk"
    TUFF = "tuff"
    GNEISS = "gneiss"
    QUARTZITE = "quartzite"
    WATER_ICE = "water_ice"
    IRON = "iron"
    CARBON = "carbon"
    LIVING_TISSUE = "living_tissue"
    PUMICE = "pumice"
    SERPENTINITE = "serpentinite"
    TRAVERTINE = "travertine"


class BuildingGrade(StrEnum):
    PLAIN = "plain"
    FINE = "fine"
    SPLENDID = "splendid"


class UndergroundStratum(StrEnum):
    PERMAFROST_LAYER = "permafrost_layer"
    AQUIFER = "aquifer"
    UNDER_OCEAN = "under_ocean"
    RESERVOIR = "reservoir"
    CAVERN_UPPER = "cavern_upper"
    CAVERN_MIDDLE = "cavern_middle"
    FAULT_ZONE = "fault_zone"
    CAVERN_LOWER = "cavern_lower"
    HOLLOW_INTERIOR = "hollow_interior"
    MAGMA_SEA = "magma_sea"
    DEEP_UNDERWORLD = "deep_underworld"


class DeepPassageKind(StrEnum):
    LEVEL = "level"
    VERTICAL = "vertical"
    OPENING = "opening"


class DeepPassageState(StrEnum):
    DIGGING = "digging"
    OPEN = "open"
    FLOODED = "flooded"
    COLLAPSED = "collapsed"
    SEALED = "sealed"


class DeepPassageOrigin(StrEnum):
    NATURAL = "natural"
    DUG = "dug"
    BREACH = "breach"
    DIVINE = "divine"
