from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.materials import ARMOUR_MATERIALS, LUXURY_MATERIALS, TOOL_MATERIALS, WEAPON_MATERIALS
from aerona.core.total import total
from aerona.domain.enums.crafts import ChemicalProduct
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.economy import CommodityKind, MaterialOrigin, WorkshopKind
from aerona.domain.enums.equipment import ArmamentSlot
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.nature_kinds import MaterialSource
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.world import WorldType
from aerona.rules.registry.body import ProstheticsRules


@dataclass(frozen=True)
class Recipe:
    techniques: tuple[Technique, ...]
    raw: CommodityKind
    made: CommodityKind | None


ORIGIN_SOURCE: Mapping[MaterialOrigin, MaterialSource] = total(
    MaterialOrigin,
    {
        MaterialOrigin.CATALOG: MaterialSource.WORLD,
        MaterialOrigin.DEAD_GOD: MaterialSource.GOD,
        MaterialOrigin.STAR: MaterialSource.STAR,
        MaterialOrigin.BEAST: MaterialSource.CREATURE,
        MaterialOrigin.RIFT: MaterialSource.RIFT,
        MaterialOrigin.RESEARCH: MaterialSource.MAKERS,
        MaterialOrigin.GOD_GIFT: MaterialSource.GOD,
        MaterialOrigin.FOSSIL: MaterialSource.WORLD,
        MaterialOrigin.LIVING_LINE: MaterialSource.CREATURE,
        MaterialOrigin.SALVAGE: MaterialSource.MAKERS,
        MaterialOrigin.OUTER_BEING: MaterialSource.RIFT,
    },
)

WORKSHOP_GOODS: dict[WorkshopKind, CommodityKind] = {
    WorkshopKind.FORGE: CommodityKind.TOOLS,
    WorkshopKind.TANNERY: CommodityKind.CLOTH,
    WorkshopKind.MILL: CommodityKind.BREAD,
    WorkshopKind.BREWERY: CommodityKind.BREW_BASE,
    WorkshopKind.WEAVERY: CommodityKind.CLOTH,
    WorkshopKind.STABLE: CommodityKind.MOUNTS,
    WorkshopKind.MASON_YARD: CommodityKind.STONE,
    WorkshopKind.CHARCOAL_KILN: CommodityKind.FUEL,
    WorkshopKind.ALCHEMIST: CommodityKind.MEDICINE,
    WorkshopKind.SHRINE_WORKSHOP: CommodityKind.SACRED_GOODS,
    WorkshopKind.SIEGE_YARD: CommodityKind.SIEGE_MATERIEL,
}

RECIPES = {
    ChemicalProduct.DYE: Recipe((Technique.HERBALISM,), CommodityKind.HERBS, CommodityKind.DYE),
    ChemicalProduct.SOAP: Recipe((Technique.HERBALISM,), CommodityKind.MEAT, None),
    ChemicalProduct.MORDANT: Recipe((Technique.ALCHEMY,), CommodityKind.ORE, CommodityKind.DYE),
    ChemicalProduct.TANNING: Recipe((Technique.HERBALISM,), CommodityKind.TIMBER, CommodityKind.CLOTH),
    ChemicalProduct.FERTILISER: Recipe((Technique.CROP_ROTATION,), CommodityKind.DUNG, None),
    ChemicalProduct.MEDICINE: Recipe((Technique.HERBALISM,), CommodityKind.HERBS, CommodityKind.MEDICINE),
    ChemicalProduct.INCENDIARY: Recipe((Technique.ALCHEMY,), CommodityKind.FUEL, CommodityKind.SIEGE_MATERIEL),
    ChemicalProduct.EXPLOSIVE: Recipe((Technique.ALCHEMY, Technique.SIEGECRAFT), CommodityKind.COAL, CommodityKind.SIEGE_MATERIEL),
    ChemicalProduct.INK: Recipe((Technique.ALPHABET,), CommodityKind.DYE, None),
    ChemicalProduct.GLAZE: Recipe((Technique.ALCHEMY,), CommodityKind.STONE, None),
    ChemicalProduct.PRESERVATIVE: Recipe((Technique.HERBALISM,), CommodityKind.HALITE, None),
    ChemicalProduct.ACID: Recipe((Technique.ALCHEMY,), CommodityKind.ORE, None),
    ChemicalProduct.SOLVENT: Recipe((Technique.INDUSTRIAL_CHEMISTRY,), CommodityKind.OIL, None),
    ChemicalProduct.ADHESIVE: Recipe((Technique.HERBALISM,), CommodityKind.LIVESTOCK, None),
}

TROPHY_CLASSES = {
    MaterialKind.GREAT_BEAST_TISSUE: ItemClass.BLADE,
    MaterialKind.IVORY: ItemClass.JEWEL,
    MaterialKind.CHITIN: ItemClass.ARMOUR,
    MaterialKind.HIDE: ItemClass.ARMOUR,
    MaterialKind.CALCIFIED_TISSUE: ItemClass.TOOL,
}

ORIGIN_WORDS = total(
    MaterialOrigin,
    {
        MaterialOrigin.CATALOG: "a known material of the world",
        MaterialOrigin.DEAD_GOD: "a dead god",
        MaterialOrigin.STAR: "a star that died",
        MaterialOrigin.BEAST: "a great beast",
        MaterialOrigin.RIFT: "a rift",
        MaterialOrigin.RESEARCH: "a material its makers found through their work",
        MaterialOrigin.GOD_GIFT: "a gift of a god",
        MaterialOrigin.FOSSIL: "a bed of what lived long ago",
        MaterialOrigin.LIVING_LINE: "a living line its makers grow",
        MaterialOrigin.SALVAGE: "a relic or wreck its finders took apart",
        MaterialOrigin.OUTER_BEING: "a substance brought from a being outside the cosmos",
    },
)

SOURCED_ORIGINS = tuple(origin for origin in MaterialOrigin if origin not in (MaterialOrigin.CATALOG, MaterialOrigin.GOD_GIFT))
ORIGIN_BASE: dict[MaterialOrigin, MaterialKind] = {
    MaterialOrigin.DEAD_GOD: MaterialKind.DIVINE_TISSUE,
    MaterialOrigin.STAR: MaterialKind.STAR_METAL,
    MaterialOrigin.BEAST: MaterialKind.GREAT_BEAST_TISSUE,
    MaterialOrigin.RIFT: MaterialKind.VOID_GLASS,
    MaterialOrigin.FOSSIL: MaterialKind.CALCIFIED_TISSUE,
    MaterialOrigin.LIVING_LINE: MaterialKind.LIVING_WOOD,
    MaterialOrigin.SALVAGE: MaterialKind.COMPOSITE,
    MaterialOrigin.RESEARCH: MaterialKind.STEEL,
}

EATING_ORDER = (
    CommodityKind.BREAD,
    CommodityKind.MEAT,
    CommodityKind.CHEESE,
    CommodityKind.LIVESTOCK,
    CommodityKind.FISH,
    CommodityKind.TUBERS,
    CommodityKind.GRAIN,
    CommodityKind.FRUIT,
    CommodityKind.EGGS,
    CommodityKind.MILK,
)

COMMONS_MATERIAL = {CommodityKind.TIMBER: MaterialKind.WOOD, CommodityKind.STONE: MaterialKind.STONE}

HULLS: Mapping[VehicleKind, tuple[MaterialKind, ...]] = total(
    VehicleKind,
    {
        VehicleKind.SHIP: (
            MaterialKind.SKYSTEEL,
            MaterialKind.STEEL,
            MaterialKind.IRON,
            MaterialKind.BRONZE,
            MaterialKind.GREAT_BEAST_TISSUE,
            MaterialKind.LIVING_WOOD,
            MaterialKind.WOOD,
        ),
        VehicleKind.GATE: (MaterialKind.CRYSTAL, MaterialKind.OBSIDIAN, MaterialKind.STONE),
        VehicleKind.BRIDGE: (MaterialKind.CRYSTAL, MaterialKind.STONE, MaterialKind.WOOD),
        VehicleKind.MOUNT: (MaterialKind.CHITIN, MaterialKind.LEATHER, MaterialKind.HIDE),
        VehicleKind.RAIL: (MaterialKind.STEEL, MaterialKind.IRON, MaterialKind.WOOD),
        VehicleKind.ROAD_VEHICLE: (MaterialKind.STEEL, MaterialKind.IRON, MaterialKind.WOOD),
        VehicleKind.AIRCRAFT: (MaterialKind.SKYSTEEL, MaterialKind.STEEL, MaterialKind.WOOD, MaterialKind.CLOTH),
        VehicleKind.TELEPORT: (MaterialKind.CRYSTAL, MaterialKind.STEEL, MaterialKind.STONE),
        VehicleKind.LIVING: (MaterialKind.LIVING_WOOD, MaterialKind.CHITIN, MaterialKind.HIDE),
        VehicleKind.RIFT: (MaterialKind.CRYSTAL, MaterialKind.OBSIDIAN, MaterialKind.STONE),
        VehicleKind.ON_FOOT: (MaterialKind.LEATHER, MaterialKind.CLOTH, MaterialKind.HIDE),
        VehicleKind.DRIFT: (MaterialKind.WOOD, MaterialKind.STONE, MaterialKind.HIDE),
    },
)

FABRICS: MappingProxyType[VehicleKind, tuple[MaterialKind, ...]] = MappingProxyType(
    {
        VehicleKind.SHIP: (MaterialKind.CLOTH, MaterialKind.LEATHER, MaterialKind.HIDE),
        VehicleKind.MOUNT: (MaterialKind.LEATHER, MaterialKind.CLOTH, MaterialKind.HIDE),
    }
)

STRUCTURE_STOCK = (
    MaterialKind.LIVING_WOOD,
    MaterialKind.HYDRAULIC_CONCRETE,
    MaterialKind.DRESSED_STONE,
    MaterialKind.LIME_MORTAR,
    MaterialKind.FIRED_BRICK,
    MaterialKind.TILE,
    MaterialKind.STONE,
    MaterialKind.RUBBLE,
    MaterialKind.MUD_BRICK,
    MaterialKind.WOOD,
    MaterialKind.THATCH,
)

HOLY_STOCK = (
    MaterialKind.GOLD,
    MaterialKind.SILVER,
    MaterialKind.CRYSTAL,
    MaterialKind.DRESSED_STONE,
    MaterialKind.STONE,
    MaterialKind.FIRED_BRICK,
    MaterialKind.MUD_BRICK,
    MaterialKind.WOOD,
)

JEWEL_STOCK = (*LUXURY_MATERIALS, MaterialKind.CALCIFIED_TISSUE, MaterialKind.WOOD)

MATERIAL_TECHNIQUES = {
    MaterialKind.BRONZE: (Technique.BRONZE,),
    MaterialKind.IRON: (Technique.IRON,),
    MaterialKind.STEEL: (Technique.STEEL,),
    MaterialKind.SKYSTEEL: (Technique.SKYSTEEL,),
}

UPGRADES: dict[MaterialKind, MaterialKind] = {MaterialKind.COPPER: MaterialKind.BRONZE, MaterialKind.IRON: MaterialKind.STEEL}

PREFERENCE: dict[CommodityKind, tuple[MaterialKind, ...]] = {
    CommodityKind.WEAPONS: WEAPON_MATERIALS,
    CommodityKind.ARMOUR: ARMOUR_MATERIALS,
    CommodityKind.TOOLS: TOOL_MATERIALS,
    CommodityKind.LUXURIES: LUXURY_MATERIALS,
}

BYPRODUCTS: MappingProxyType[MaterialKind, tuple[MaterialKind, int]] = MappingProxyType(
    {MaterialKind.LEAD: (MaterialKind.SILVER, 10), MaterialKind.COPPER: (MaterialKind.GOLD, 3), MaterialKind.IRON: (MaterialKind.SULFUR, 5)}
)

REQUIRED: MappingProxyType[CommodityKind, tuple[KnowledgeBranch, int]] = MappingProxyType(
    {
        CommodityKind.FISH: (KnowledgeBranch.SEAFARING, 0),
        CommodityKind.MOUNTS: (KnowledgeBranch.AGRICULTURE, 1),
        CommodityKind.MAGICAL_REAGENTS: (KnowledgeBranch.MAGIC, 1),
    }
)

DIFFICULTY: MappingProxyType[CommodityKind, int] = MappingProxyType(
    {CommodityKind.ORE: 55, CommodityKind.STONE: 40, CommodityKind.TIMBER: 30, CommodityKind.FISH: 25, CommodityKind.MAGICAL_REAGENTS: 45}
)

WORLD_MINERALS: dict[WorldType, tuple[MaterialKind, ...]] = {
    WorldType.IRON: (MaterialKind.IRON, MaterialKind.LEAD),
    WorldType.CARBON: (MaterialKind.GEMS,),
    WorldType.GREENHOUSE: (MaterialKind.SULFUR,),
    WorldType.CHTHONIAN: (MaterialKind.IRON, MaterialKind.GOLD),
    WorldType.HYCEAN: (MaterialKind.HALITE,),
    WorldType.JUNGLE: (MaterialKind.AMBER,),
    WorldType.FORGE: (MaterialKind.IRON, MaterialKind.COPPER),
    WorldType.SHATTERED: (MaterialKind.STAR_METAL,),
    WorldType.HOLLOW: (MaterialKind.GEMS,),
    WorldType.ICE_SHELL: (MaterialKind.HALITE,),
}

FORGED: MappingProxyType[CommodityKind, tuple[ArmamentSlot, ...]] = MappingProxyType(
    {
        CommodityKind.WEAPONS: (ArmamentSlot.HAND_WEAPON, ArmamentSlot.MISSILE_WEAPON),
        CommodityKind.ARMOUR: (ArmamentSlot.ARMOUR, ArmamentSlot.SHIELD, ArmamentSlot.HELMET, ArmamentSlot.BARDING),
        CommodityKind.SIEGE_MATERIEL: (ArmamentSlot.VEHICLE_WEAPON,),
    }
)

FOODS = (CommodityKind.GRAIN, CommodityKind.BREAD, CommodityKind.FISH, CommodityKind.LIVESTOCK)

PUT_OUT: MappingProxyType[CommodityKind, CommodityKind] = MappingProxyType(
    {
        CommodityKind.WOOL: CommodityKind.CLOTH,
        CommodityKind.FIBRE: CommodityKind.CLOTH,
        CommodityKind.TIMBER: CommodityKind.TOOLS,
        CommodityKind.ORE: CommodityKind.TOOLS,
    }
)

STRATEGIC_INPUTS: dict[CommodityKind, tuple[CommodityKind, ...]] = {
    CommodityKind.ORE: (CommodityKind.WEAPONS, CommodityKind.ARMOUR, CommodityKind.TOOLS),
    CommodityKind.LIVESTOCK: (CommodityKind.MOUNTS,),
    CommodityKind.TIMBER: (CommodityKind.SIEGE_MATERIEL,),
}

UPKEEP_MATERIALS: MappingProxyType[CommodityKind, MaterialKind] = MappingProxyType(
    {
        CommodityKind.STONE: MaterialKind.STONE,
        CommodityKind.TIMBER: MaterialKind.WOOD,
        CommodityKind.ORE: MaterialKind.IRON,
        CommodityKind.CLOTH: MaterialKind.CLOTH,
    }
)

YARD_ROLES: MappingProxyType[WorkshopKind, tuple[UnitKind, ...]] = MappingProxyType(
    {
        WorkshopKind.SHIPYARD: (UnitKind.NAVAL_CREW,),
        WorkshopKind.SIEGE_YARD: (UnitKind.SIEGE_CREW, UnitKind.ARTILLERY_CREW, UnitKind.VEHICLE_CREW),
        WorkshopKind.STABLE: (UnitKind.CHARIOTS,),
    }
)


WORKABILITY: Mapping[MaterialKind, Callable[[ProstheticsRules], int]] = {
    MaterialKind.WOOD: lambda rules: rules.wood,
    MaterialKind.CALCIFIED_TISSUE: lambda rules: rules.calcified_tissue,
    MaterialKind.IVORY: lambda rules: rules.ivory,
    MaterialKind.COPPER: lambda rules: rules.copper,
    MaterialKind.BRONZE: lambda rules: rules.bronze,
    MaterialKind.IRON: lambda rules: rules.iron,
    MaterialKind.STEEL: lambda rules: rules.steel,
    MaterialKind.SILVER: lambda rules: rules.silver,
    MaterialKind.GOLD: lambda rules: rules.gold,
    MaterialKind.GLASS: lambda rules: rules.glass,
    MaterialKind.CRYSTAL: lambda rules: rules.crystal,
    MaterialKind.STAR_METAL: lambda rules: rules.star_metal,
    MaterialKind.LIVING_WOOD: lambda rules: rules.living_wood,
    MaterialKind.GREAT_BEAST_TISSUE: lambda rules: rules.great_beast_tissue,
    MaterialKind.SKYSTEEL: lambda rules: rules.skysteel,
}
