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
    also: frozenset[ProductPart] = frozenset()
    feeds_pollinators: bool = False

    @property
    def yields(self) -> frozenset[ProductPart]:
        return self.also | {self.product}


FORMS: MappingProxyType[PlantForm, FormSpec] = total(
    F,
    {
        F.TREE: FormSpec("Tree", (P.WOOD, P.BARK, P.LEAF, P.FRUIT, P.SEED, P.SAP, P.RESIN), R.ANIMAL_SEED, 200, True, False),
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
        F.EPIPHYTE: FormSpec("Epiphyte", (P.LEAF, P.FLOWER, P.SPORE), R.WIND_SEED, 20, True, False),
        F.PARASITIC: FormSpec("Parasitic plant", (P.STEM, P.FLOWER, P.SEED), R.ANIMAL_SEED, 5, False, False),
        F.PALM: FormSpec("Palm", (P.WOOD, P.FRUIT, P.SAP, P.FIBRE, P.LEAF), R.ANIMAL_SEED, 80, True, False),
        F.GEOPHYTE: FormSpec("Geophyte", (P.TUBER, P.ROOT, P.FLOWER, P.NECTAR), R.RUNNER, 10, False, False),
    },
)

PARTS: MappingProxyType[PlantPart, PartSpec] = total(
    P,
    {
        P.ROOT: PartSpec("Root", CommodityKind.HERBS, ProductPart.ROOT, frozenset({ProductPart.SPICE, ProductPart.TOXIN})),
        P.TUBER: PartSpec("Tuber", CommodityKind.TUBERS, ProductPart.ROOT, frozenset({ProductPart.SUGAR})),
        P.STEM: PartSpec("Stem", CommodityKind.FODDER, ProductPart.FIBRE, frozenset({ProductPart.FODDER, ProductPart.SUGAR})),
        P.WOOD: PartSpec("Wood", CommodityKind.TIMBER, ProductPart.WOOD),
        P.BARK: PartSpec("Bark", CommodityKind.MEDICINE, ProductPart.DYE, frozenset({ProductPart.SPICE, ProductPart.STIMULANT})),
        P.LEAF: PartSpec("Leaf", CommodityKind.HERBS, ProductPart.LEAF, frozenset({ProductPart.STIMULANT, ProductPart.FODDER, ProductPart.TOXIN})),
        P.FLOWER: PartSpec("Flower", CommodityKind.DYE, ProductPart.DYE, frozenset({ProductPart.SPICE, ProductPart.OIL})),
        P.FRUIT: PartSpec("Fruit", CommodityKind.FRUIT, ProductPart.FRUIT, frozenset({ProductPart.OIL, ProductPart.SUGAR, ProductPart.SPICE})),
        P.SEED: PartSpec("Seed", CommodityKind.GRAIN, ProductPart.SEED, frozenset({ProductPart.OIL, ProductPart.SPICE, ProductPart.STIMULANT})),
        P.SAP: PartSpec("Sap", CommodityKind.BREW_BASE, ProductPart.SAP, frozenset({ProductPart.SUGAR, ProductPart.RESIN})),
        P.FIBRE: PartSpec("Fibre", CommodityKind.FIBRE, ProductPart.FIBRE),
        P.SPORE: PartSpec("Spore", CommodityKind.MAGICAL_REAGENTS, ProductPart.REAGENT, frozenset({ProductPart.TOXIN})),
        P.RESIN: PartSpec("Resin", CommodityKind.INCENSE, ProductPart.RESIN),
        P.POLLEN: PartSpec("Pollen", CommodityKind.HERBS, ProductPart.REAGENT, frozenset({ProductPart.SUGAR}), feeds_pollinators=True),
        P.NECTAR: PartSpec("Nectar", CommodityKind.HONEY, ProductPart.SUGAR, frozenset({ProductPart.STIMULANT}), feeds_pollinators=True),
    },
)
