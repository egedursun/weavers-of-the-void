from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.ecology import Biochemistry, GrowthCycle, PlantYield, SpeciesClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.world import Atmosphere, WorldType
from aerona.rules.registry import Rules

B = Biochemistry
Y = PlantYield
C = CommodityKind


@dataclass(frozen=True)
class PlantProduct:
    product: PlantYield
    label: str
    commodity: CommodityKind
    material: MaterialKind | None
    rate: int
    food: bool
    worth: Callable[[Rules], int]


PLANT_PRODUCTS: MappingProxyType[PlantYield, PlantProduct] = MappingProxyType(
    {
        item.product: item
        for item in (
            PlantProduct(Y.OIL, "Oil", C.FUEL, None, 1, False, lambda rules: rules.plant_products.oil_value),
            PlantProduct(Y.SUGAR, "Sugar", C.BREW_BASE, None, 1, True, lambda rules: rules.plant_products.sugar_value),
            PlantProduct(Y.SPICE, "Spice", C.LUXURIES, None, 1, False, lambda rules: rules.plant_products.spice_value),
            PlantProduct(Y.RESIN, "Resin", C.INCENSE, None, 1, False, lambda rules: rules.plant_products.resin_value),
            PlantProduct(Y.STIMULANT, "Stimulant", C.HERBS, None, 1, False, lambda rules: rules.plant_products.stimulant_value),
            PlantProduct(Y.FODDER, "Fodder", C.FODDER, None, 2, False, lambda rules: rules.plant_products.fodder_value),
            PlantProduct(Y.GRAIN, "Grain", C.GRAIN, None, 2, True, lambda rules: rules.plant_products.grain_value),
            PlantProduct(Y.TUBER, "Tubers", C.TUBERS, None, 2, True, lambda rules: rules.plant_products.tuber_value),
            PlantProduct(Y.FRUIT, "Fruit", C.FRUIT, None, 2, True, lambda rules: rules.plant_products.fruit_value),
            PlantProduct(Y.FIBRE, "Fibre", C.FIBRE, None, 1, False, lambda rules: rules.plant_products.fibre_value),
            PlantProduct(Y.DYE, "Dye", C.DYE, None, 1, False, lambda rules: rules.plant_products.dye_value),
            PlantProduct(Y.TIMBER, "Timber", C.TIMBER, MaterialKind.WOOD, 1, False, lambda rules: rules.plant_products.timber_value),
            PlantProduct(Y.HERB, "Herbs", C.HERBS, None, 1, False, lambda rules: rules.plant_products.herb_value),
            PlantProduct(Y.BREW_BASE, "Brew base", C.BREW_BASE, None, 1, False, lambda rules: rules.plant_products.brew_base_value),
            PlantProduct(Y.REAGENT, "Alchemical reagent", C.MAGICAL_REAGENTS, None, 1, False, lambda rules: rules.plant_products.reagent_value),
            PlantProduct(Y.POISON, "Poison", C.POISON, None, 1, False, lambda rules: rules.plant_products.poison_value),
        )
    }
)
PRODUCT_BY_NAME: MappingProxyType[str, PlantProduct] = MappingProxyType({item.product.value: item for item in PLANT_PRODUCTS.values()})
PRODUCT_BY_COMMODITY: MappingProxyType[CommodityKind, PlantProduct] = MappingProxyType({item.commodity: item for item in PLANT_PRODUCTS.values()})


def plant_product_of(product: str, commodity: CommodityKind | None) -> PlantProduct | None:
    return PRODUCT_BY_NAME.get(product) or (PRODUCT_BY_COMMODITY.get(commodity) if commodity is not None else None)


DEFAULT_YIELDS: MappingProxyType[tuple[SpeciesClass, GrowthCycle], tuple[PlantYield, ...]] = MappingProxyType(
    {
        (SpeciesClass.PLANT, GrowthCycle.ANNUAL): (Y.GRAIN,),
        (SpeciesClass.PLANT, GrowthCycle.PERENNIAL): (Y.FRUIT, Y.HERB),
        (SpeciesClass.PLANT, GrowthCycle.TREE): (Y.TIMBER, Y.FRUIT),
        (SpeciesClass.FUNGUS, GrowthCycle.ANNUAL): (Y.HERB,),
        (SpeciesClass.FUNGUS, GrowthCycle.PERENNIAL): (Y.HERB,),
        (SpeciesClass.FUNGUS, GrowthCycle.TREE): (Y.HERB,),
    }
)
ATMOSPHERE_LIFE: MappingProxyType[Atmosphere, tuple[Biochemistry, ...]] = MappingProxyType(
    {
        Atmosphere.NORMAL: (B.CARBON_WATER,),
        Atmosphere.DENSE: (B.CARBON_WATER, B.CARBON_AMMONIA),
        Atmosphere.THIN: (B.CARBON_WATER, B.SILICON),
        Atmosphere.TOXIC: (B.CARBON_AMMONIA, B.SILICON),
        Atmosphere.NONE: (B.SILICON, B.CRYSTAL),
    }
)
WORLD_TYPE_LIFE: MappingProxyType[WorldType, tuple[Biochemistry, ...]] = MappingProxyType(
    {
        WorldType.CRYSTAL: (B.CRYSTAL,),
        WorldType.ICE: (B.CARBON_AMMONIA, B.CARBON_METHANE),
        WorldType.ICE_GIANT: (B.CARBON_METHANE, B.CARBON_AMMONIA),
        WorldType.GAS: (B.CARBON_AMMONIA,),
        WorldType.HOT_GIANT: (B.CARBON_AMMONIA, B.SILICON, B.PLASMA),
        WorldType.LAVA: (B.SILICON,),
        WorldType.FORGE: (B.SILICON,),
        WorldType.IRON: (B.SILICON,),
        WorldType.CHTHONIAN: (B.SILICON,),
        WorldType.CARBON: (B.CARBON_WATER, B.CARBON_AMMONIA),
        WorldType.DREAM: (B.SPIRIT,),
        WorldType.GODS_PALACE: (B.SPIRIT,),
        WorldType.CORPSE_WORLD: (B.SPIRIT,),
        WorldType.DEAD: (B.SPIRIT, B.SILICON),
        WorldType.VOID_POCKET: (B.VOID,),
    }
)
BIOCHEMISTRY_LABELS: MappingProxyType[Biochemistry, str] = total(
    Biochemistry,
    {
        B.CARBON_WATER: "Carbon and water",
        B.CARBON_AMMONIA: "Carbon and ammonia",
        B.SILICON: "Silicon",
        B.CRYSTAL: "Crystal",
        B.VOID: "Void",
        B.SPIRIT: "Spirit",
        B.CARBON_METHANE: "Carbon and methane",
        B.PLASMA: "Plasma",
    },
)


def world_life(world_type: WorldType, atmosphere: Atmosphere) -> tuple[Biochemistry, ...]:
    return tuple(dict.fromkeys((*ATMOSPHERE_LIFE[atmosphere], *WORLD_TYPE_LIFE.get(world_type, ()))))
