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


class BuildingGrade(StrEnum):
    PLAIN = "plain"
    FINE = "fine"
    SPLENDID = "splendid"


class UndergroundStratum(StrEnum):
    AQUIFER = "aquifer"
    CAVERN_UPPER = "cavern_upper"
    CAVERN_MIDDLE = "cavern_middle"
    CAVERN_DEEP = "cavern_deep"
    MAGMA_SEA = "magma_sea"
    DEEP_UNDERWORLD = "deep_underworld"
    UNDER_OCEAN = "under_ocean"
    HOLLOW_INTERIOR = "hollow_interior"
    RESERVOIR = "reservoir"
