from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.materials import ARMOUR_MATERIALS, LUXURY_MATERIALS, TOOL_MATERIALS, WEAPON_MATERIALS
from aerona.domain.enums.economy import CommodityFamily, CommodityKind
from aerona.domain.enums.material import MINERAL_KINDS, MaterialKind
from aerona.domain.enums.society import Commodity
from aerona.rules.registry import Rules

C = CommodityKind
F = CommodityFamily
M = MaterialKind


@dataclass(frozen=True)
class CommoditySpec:
    kind: CommodityKind
    label: str
    family: CommodityFamily
    aggregate: Commodity
    base_price: int
    nourishment: int = 0
    materials: tuple[MaterialKind, ...] = ()
    consumption: Callable[[Rules], int] = lambda rules: 0
    strategic: bool = False


COMMODITIES: MappingProxyType[CommodityKind, CommoditySpec] = MappingProxyType(
    {
        item.kind: item
        for item in (
            CommoditySpec(C.GRAIN, "Grain", F.SUBSISTENCE, Commodity.FOOD, 100, 10, consumption=lambda rules: rules.consumption.grain_per_1000),
            CommoditySpec(C.LIVESTOCK, "Livestock", F.SUBSISTENCE, Commodity.FOOD, 140, 12, consumption=lambda rules: rules.consumption.livestock_per_1000),
            CommoditySpec(C.FISH, "Fish", F.SUBSISTENCE, Commodity.FOOD, 110, 9, consumption=lambda rules: rules.consumption.fish_per_1000),
            CommoditySpec(C.BREAD, "Bread", F.SUBSISTENCE, Commodity.FOOD, 130, 14, consumption=lambda rules: rules.consumption.bread_per_1000),
            CommoditySpec(C.FODDER, "Fodder", F.SUBSISTENCE, Commodity.FOOD, 60, consumption=lambda rules: rules.consumption.fodder_per_1000),
            CommoditySpec(C.MEAT, "Meat", F.SUBSISTENCE, Commodity.FOOD, 150, 14, consumption=lambda rules: rules.consumption.meat_per_1000),
            CommoditySpec(C.MILK, "Milk", F.SUBSISTENCE, Commodity.FOOD, 90, 7, consumption=lambda rules: rules.consumption.milk_per_1000),
            CommoditySpec(C.CHEESE, "Cheese", F.SUBSISTENCE, Commodity.FOOD, 160, 15, consumption=lambda rules: rules.consumption.cheese_per_1000),
            CommoditySpec(C.FRUIT, "Fruit", F.SUBSISTENCE, Commodity.FOOD, 100, 6, consumption=lambda rules: rules.consumption.fruit_per_1000),
            CommoditySpec(C.TUBERS, "Tubers", F.SUBSISTENCE, Commodity.FOOD, 70, 9, consumption=lambda rules: rules.consumption.tubers_per_1000),
            CommoditySpec(
                C.TIMBER,
                "Timber",
                F.SUBSISTENCE,
                Commodity.GOODS,
                80,
                materials=(M.WOOD, M.LIVING_WOOD),
                consumption=lambda rules: rules.consumption.timber_per_1000,
            ),
            CommoditySpec(C.FUEL, "Fuel", F.SUBSISTENCE, Commodity.GOODS, 70, consumption=lambda rules: rules.consumption.fuel_per_1000),
            CommoditySpec(C.COAL, "Coal", F.INDUSTRIAL, Commodity.GOODS, 90, consumption=lambda rules: rules.consumption.coal_per_1000),
            CommoditySpec(C.PEAT, "Peat", F.SUBSISTENCE, Commodity.GOODS, 45, consumption=lambda rules: rules.consumption.peat_per_1000),
            CommoditySpec(C.DUNG, "Dung", F.SUBSISTENCE, Commodity.GOODS, 20, consumption=lambda rules: rules.consumption.dung_per_1000),
            CommoditySpec(C.EGGS, "Eggs", F.SUBSISTENCE, Commodity.FOOD, 80, 8, consumption=lambda rules: rules.consumption.eggs_per_1000),
            CommoditySpec(C.WOOL, "Wool", F.SUBSISTENCE, Commodity.GOODS, 90, consumption=lambda rules: rules.consumption.wool_per_1000),
            CommoditySpec(C.FIBRE, "Plant fibre", F.SUBSISTENCE, Commodity.GOODS, 60, consumption=lambda rules: rules.consumption.fibre_per_1000),
            CommoditySpec(C.DYE, "Dye", F.LUXURY, Commodity.GOODS, 150, consumption=lambda rules: rules.consumption.dye_per_1000),
            CommoditySpec(C.HERBS, "Herbs", F.SUBSISTENCE, Commodity.GOODS, 70, consumption=lambda rules: rules.consumption.herbs_per_1000),
            CommoditySpec(C.BREW_BASE, "Brew base", F.SUBSISTENCE, Commodity.GOODS, 65, consumption=lambda rules: rules.consumption.brew_base_per_1000),
            CommoditySpec(C.POISON, "Poison", F.STRATEGIC, Commodity.GOODS, 180, consumption=lambda rules: rules.consumption.poison_per_1000),
            CommoditySpec(
                C.ORE,
                "Ore",
                F.INDUSTRIAL,
                Commodity.ORE,
                110,
                materials=tuple(sorted(MINERAL_KINDS)),
                consumption=lambda rules: rules.consumption.ore_per_1000,
            ),
            CommoditySpec(
                C.STONE,
                "Stone",
                F.INDUSTRIAL,
                Commodity.ORE,
                70,
                materials=(M.STONE, M.CLAY, M.OBSIDIAN, M.FLINT),
                consumption=lambda rules: rules.consumption.stone_per_1000,
            ),
            CommoditySpec(
                C.CLOTH,
                "Cloth",
                F.INDUSTRIAL,
                Commodity.GOODS,
                120,
                materials=(M.CLOTH, M.HIDE, M.LEATHER),
                consumption=lambda rules: rules.consumption.cloth_per_1000,
            ),
            CommoditySpec(
                C.TOOLS,
                "Tools",
                F.INDUSTRIAL,
                Commodity.GOODS,
                150,
                materials=TOOL_MATERIALS,
                consumption=lambda rules: rules.consumption.tools_per_1000,
            ),
            CommoditySpec(
                C.WEAPONS,
                "Weapons",
                F.STRATEGIC,
                Commodity.GOODS,
                220,
                materials=WEAPON_MATERIALS,
                consumption=lambda rules: rules.consumption.weapons_per_1000,
                strategic=True,
            ),
            CommoditySpec(
                C.ARMOUR,
                "Armour",
                F.STRATEGIC,
                Commodity.GOODS,
                240,
                materials=ARMOUR_MATERIALS,
                consumption=lambda rules: rules.consumption.armour_per_1000,
                strategic=True,
            ),
            CommoditySpec(
                C.MOUNTS,
                "Mounts",
                F.STRATEGIC,
                Commodity.GOODS,
                260,
                consumption=lambda rules: rules.consumption.mounts_per_1000,
                strategic=True,
            ),
            CommoditySpec(
                C.SIEGE_MATERIEL,
                "Siege materiel",
                F.STRATEGIC,
                Commodity.GOODS,
                200,
                materials=(M.WOOD, M.IRON),
                consumption=lambda rules: rules.consumption.siege_materiel_per_1000,
                strategic=True,
            ),
            CommoditySpec(C.MEDICINE, "Medicine", F.STRATEGIC, Commodity.GOODS, 230, consumption=lambda rules: rules.consumption.medicine_per_1000),
            CommoditySpec(
                C.LUXURIES,
                "Luxuries",
                F.LUXURY,
                Commodity.GOODS,
                300,
                materials=LUXURY_MATERIALS,
                consumption=lambda rules: rules.consumption.luxuries_per_1000,
            ),
            CommoditySpec(
                C.INCENSE,
                "Incense",
                F.LUXURY,
                Commodity.GOODS,
                180,
                materials=(M.AMBER, M.WOOD),
                consumption=lambda rules: rules.consumption.incense_per_1000,
            ),
            CommoditySpec(C.SACRED_GOODS, "Sacred goods", F.LUXURY, Commodity.GOODS, 260, consumption=lambda rules: rules.consumption.sacred_goods_per_1000),
            CommoditySpec(
                C.MAGICAL_REAGENTS,
                "Magical reagents",
                F.LUXURY,
                Commodity.GOODS,
                320,
                materials=(M.CRYSTAL, M.SULFUR, M.SALT),
                consumption=lambda rules: rules.consumption.magical_reagents_per_1000,
                strategic=True,
            ),
        )
    }
)

FOOD_KINDS = tuple(kind for kind, item in COMMODITIES.items() if item.nourishment > 0)
STRATEGIC_KINDS = tuple(kind for kind, item in COMMODITIES.items() if item.strategic)
BACKFILL_SPLITS: MappingProxyType[Commodity, tuple[tuple[CommodityKind, int], ...]] = MappingProxyType(
    {
        Commodity.FOOD: ((C.GRAIN, 55), (C.LIVESTOCK, 25), (C.FISH, 10), (C.FODDER, 10)),
        Commodity.ORE: ((C.ORE, 70), (C.STONE, 30)),
        Commodity.GOODS: ((C.TOOLS, 25), (C.CLOTH, 20), (C.TIMBER, 20), (C.FUEL, 15), (C.WEAPONS, 10), (C.LUXURIES, 10)),
    }
)


def commodity_label(kind: CommodityKind) -> str:
    return COMMODITIES[kind].label
