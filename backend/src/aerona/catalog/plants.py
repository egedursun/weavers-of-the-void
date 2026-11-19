from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.nature_kinds import ProductPart
from aerona.domain.enums.plants import PlantForm, PlantPart, PlantReproduction

F = PlantForm
P = PlantPart
R = PlantReproduction


@dataclass(frozen=True)
class FormSpec:
    label: str
    parts: tuple[PlantPart, ...]
    reproduction: PlantReproduction
    lifespan_years: int
    storm_prone: bool
    fire_prone: bool


@dataclass(frozen=True)
class PartSpec:
    label: str
    commodity: CommodityKind | None
    product: ProductPart


FORMS: MappingProxyType[PlantForm, FormSpec] = total(
    F,
    {
        F.TREE: FormSpec("Tree", (P.WOOD, P.BARK, P.LEAF, P.FRUIT, P.SEED, P.SAP), R.ANIMAL_SEED, 200, True, False),
        F.SHRUB: FormSpec("Shrub", (P.WOOD, P.LEAF, P.FLOWER, P.FRUIT), R.ANIMAL_SEED, 30, False, True),
        F.HERB: FormSpec("Herb", (P.LEAF, P.FLOWER, P.ROOT, P.SEED), R.WIND_SEED, 2, False, True),
        F.GRASS: FormSpec("Grass", (P.SEED, P.STEM, P.FIBRE), R.WIND_SEED, 1, False, True),
        F.VINE: FormSpec("Vine", (P.FRUIT, P.LEAF, P.STEM), R.ANIMAL_SEED, 40, True, False),
        F.SUCCULENT: FormSpec("Succulent", (P.SAP, P.LEAF, P.FLOWER), R.CUTTING, 50, False, False),
        F.AQUATIC: FormSpec("Aquatic plant", (P.LEAF, P.ROOT, P.STEM), R.RUNNER, 5, False, False),
        F.MOSS_LIKE: FormSpec("Moss-like", (P.LEAF, P.SPORE), R.SPORE, 10, False, True),
        F.FUNGUS_LIKE: FormSpec("Fungus-like", (P.SPORE, P.STEM), R.SPORE, 3, False, False),
        F.COLONIAL: FormSpec("Colonial", (P.SAP, P.SPORE), R.SPORE, 500, False, False),
        F.MADE: FormSpec("Made plant", (P.SEED, P.FIBRE), R.MADE, 10, False, False),
    },
)

PARTS: MappingProxyType[PlantPart, PartSpec] = total(
    P,
    {
        P.ROOT: PartSpec("Root", CommodityKind.HERBS, ProductPart.ROOT),
        P.TUBER: PartSpec("Tuber", CommodityKind.TUBERS, ProductPart.ROOT),
        P.STEM: PartSpec("Stem", CommodityKind.FODDER, ProductPart.FIBRE),
        P.WOOD: PartSpec("Wood", CommodityKind.TIMBER, ProductPart.WOOD),
        P.BARK: PartSpec("Bark", CommodityKind.MEDICINE, ProductPart.DYE),
        P.LEAF: PartSpec("Leaf", CommodityKind.HERBS, ProductPart.LEAF),
        P.FLOWER: PartSpec("Flower", CommodityKind.DYE, ProductPart.DYE),
        P.FRUIT: PartSpec("Fruit", CommodityKind.FRUIT, ProductPart.FRUIT),
        P.SEED: PartSpec("Seed", CommodityKind.GRAIN, ProductPart.SEED),
        P.SAP: PartSpec("Sap", CommodityKind.BREW_BASE, ProductPart.SAP),
        P.FIBRE: PartSpec("Fibre", CommodityKind.FIBRE, ProductPart.FIBRE),
        P.SPORE: PartSpec("Spore", CommodityKind.MAGICAL_REAGENTS, ProductPart.REAGENT),
    },
)
