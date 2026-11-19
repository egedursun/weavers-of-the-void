from enum import StrEnum


class PlantForm(StrEnum):
    TREE = "tree"
    SHRUB = "shrub"
    HERB = "herb"
    GRASS = "grass"
    VINE = "vine"
    SUCCULENT = "succulent"
    AQUATIC = "aquatic"
    MOSS_LIKE = "moss_like"
    FUNGUS_LIKE = "fungus_like"
    COLONIAL = "colonial"
    MADE = "made"


class PlantPart(StrEnum):
    ROOT = "root"
    TUBER = "tuber"
    STEM = "stem"
    WOOD = "wood"
    BARK = "bark"
    LEAF = "leaf"
    FLOWER = "flower"
    FRUIT = "fruit"
    SEED = "seed"
    SAP = "sap"
    FIBRE = "fibre"
    SPORE = "spore"


class PlantReproduction(StrEnum):
    WIND_SEED = "wind_seed"
    ANIMAL_SEED = "animal_seed"
    SPORE = "spore"
    RUNNER = "runner"
    CUTTING = "cutting"
    MADE = "made"
