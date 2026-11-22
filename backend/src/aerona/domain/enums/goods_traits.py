from enum import StrEnum


class CommodityTrait(StrEnum):
    CASH_CROP = "cash_crop"
    HEAT_STOCK = "heat_stock"
    OFFERING = "offering"
    STAPLE = "staple"
    HOARD = "hoard"
    DUG = "dug"
    RAW_MATERIAL = "raw_material"
    HEALING = "healing"
    KEEPING = "keeping"
    STORED_GRAIN = "stored_grain"
    WAR_GOOD = "war_good"
    CIVILIAN = "civilian"
    WOODY = "woody"
    RENEWABLE = "renewable"
    FOOD_STARCH = "food_starch"
    FOOD_PROTEIN = "food_protein"
    FOOD_FAT = "food_fat"
    FOOD_FRESH = "food_fresh"
    FOOD_MINERAL = "food_mineral"
    FOOD_SPECIAL = "food_special"


class MaterialTrait(StrEnum):
    MINERAL = "mineral"
    PRECIOUS = "precious"
    METAL_SEAM = "metal_seam"
    STONE_SEAM = "stone_seam"
    RARE_SEAM = "rare_seam"
    RESERVE = "reserve"
    ORGANIC_CLOTH = "organic_cloth"
    STRATEGIC = "strategic"
    STONY = "stony"
    STONE_KIND = "stone_kind"
    COMMON = "common"
    FEVER = "fever"
    CONSTRUCT_BODY = "construct_body"


class WorkshopTrait(StrEnum):
    SMELTING = "smelting"
    MILLING = "milling"
    TRADING = "trading"
    CELLAR = "cellar"
    CART_WORKS = "cart_works"
