from enum import StrEnum


class MaterialKind(StrEnum):
    WOOD = "wood"
    BONE = "bone"
    HIDE = "hide"
    LEATHER = "leather"
    CLOTH = "cloth"
    STONE = "stone"
    FLINT = "flint"
    OBSIDIAN = "obsidian"
    COPPER = "copper"
    TIN = "tin"
    BRONZE = "bronze"
    IRON = "iron"
    STEEL = "steel"
    SILVER = "silver"
    GOLD = "gold"
    GLASS = "glass"
    CRYSTAL = "crystal"
    IVORY = "ivory"
    CHITIN = "chitin"
    DRAGONBONE = "dragonbone"
    STAR_METAL = "star_metal"
    VOID_GLASS = "void_glass"
    GODFLESH = "godflesh"
    LIVING_WOOD = "living_wood"
    SALT = "salt"
    AMBER = "amber"
    LEAD = "lead"
    SKYSTEEL = "skysteel"
    SULFUR = "sulfur"
    CLAY = "clay"
    GEMS = "gems"
    MUD_BRICK = "mud_brick"
    FIRED_BRICK = "fired_brick"
    DRESSED_STONE = "dressed_stone"
    RUBBLE = "rubble"
    LIME_MORTAR = "lime_mortar"
    HYDRAULIC_CONCRETE = "hydraulic_concrete"
    THATCH = "thatch"
    TILE = "tile"


MINERAL_KINDS = frozenset(
    {
        MaterialKind.STONE,
        MaterialKind.FLINT,
        MaterialKind.OBSIDIAN,
        MaterialKind.COPPER,
        MaterialKind.TIN,
        MaterialKind.IRON,
        MaterialKind.SILVER,
        MaterialKind.GOLD,
        MaterialKind.CRYSTAL,
        MaterialKind.SALT,
        MaterialKind.AMBER,
        MaterialKind.LEAD,
        MaterialKind.SULFUR,
        MaterialKind.CLAY,
        MaterialKind.GEMS,
        MaterialKind.STAR_METAL,
        MaterialKind.VOID_GLASS,
    }
)
