from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.economy import CommodityKind, MaterialFamily
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.settlement import BuildMaterial
from aerona.domain.enums.society import KnowledgeBranch

M = MaterialKind
F = MaterialFamily
B = KnowledgeBranch


@dataclass(frozen=True)
class MaterialSpec:
    kind: MaterialKind
    label: str
    family: MaterialFamily
    hardness: int
    toughness: int
    weight: int
    edge: int
    conductivity: int
    sanctity: int
    corruption: int
    rarity: int
    base_value: int
    decay: int
    branch: KnowledgeBranch | None = None
    level: int = 0
    gate: KnowledgeBranch | None = None
    melting_point: int = 100
    ignition_point: int = 100
    boiling_point: int = 100
    density: int = 50
    impact_yield: int = 50
    impact_fracture: int = 50
    shear_yield: int = 50
    shear_fracture: int = 50
    elasticity: int = 0
    thermal_conductivity: int = 50
    solid_density: int = 50
    max_edge: int = 0


def spec(
    head: tuple[MaterialKind, str, MaterialFamily], physics: tuple[int, int, int, int], spirit: tuple[int, int, int], economy: tuple[int, int, int]
) -> MaterialSpec:
    kind, label, family = head
    hardness, toughness, weight, edge = physics
    conductivity, sanctity, corruption = spirit
    rarity, base_value, decay = economy
    return MaterialSpec(kind, label, family, hardness, toughness, weight, edge, conductivity, sanctity, corruption, rarity, base_value, decay)


def worked(material: MaterialSpec, branch: KnowledgeBranch, level: int, gate: KnowledgeBranch | None = None) -> MaterialSpec:
    return MaterialSpec(**{**material.__dict__, "branch": branch, "level": level, "gate": gate})


PHYSICS_FIELDS = (
    "melting_point",
    "ignition_point",
    "boiling_point",
    "density",
    "impact_yield",
    "impact_fracture",
    "shear_yield",
    "shear_fracture",
    "elasticity",
    "thermal_conductivity",
    "solid_density",
    "max_edge",
)
PHYSICS: MappingProxyType[MaterialKind, tuple[int, ...]] = MappingProxyType(
    {
        M.WOOD: (100, 25, 100, 30, 20, 35, 15, 30, 55, 10, 30, 15),
        M.CALCIFIED_TISSUE: (100, 45, 100, 40, 30, 45, 25, 40, 20, 15, 40, 30),
        M.HIDE: (100, 35, 100, 20, 15, 45, 8, 35, 40, 8, 20, 0),
        M.LEATHER: (100, 35, 100, 20, 22, 55, 15, 45, 35, 8, 20, 0),
        M.CLOTH: (100, 20, 100, 8, 5, 25, 3, 20, 30, 6, 8, 0),
        M.STONE: (85, 100, 100, 80, 55, 50, 50, 45, 0, 35, 82, 15),
        M.FLINT: (80, 100, 100, 55, 60, 30, 65, 40, 0, 30, 58, 70),
        M.OBSIDIAN: (60, 100, 100, 50, 55, 15, 62, 25, 0, 25, 52, 95),
        M.CLAY: (70, 100, 100, 55, 20, 20, 18, 20, 5, 25, 60, 0),
        M.HALITE: (40, 100, 75, 40, 10, 10, 10, 10, 0, 40, 42, 0),
        M.SULFUR: (15, 20, 30, 35, 8, 10, 8, 10, 0, 10, 38, 0),
        M.COPPER: (55, 100, 85, 65, 35, 55, 30, 50, 25, 90, 68, 35),
        M.TIN: (30, 100, 80, 58, 18, 40, 15, 35, 20, 60, 60, 15),
        M.BRONZE: (52, 100, 85, 68, 50, 65, 48, 62, 30, 70, 70, 55),
        M.IRON: (68, 100, 90, 72, 60, 70, 58, 68, 30, 60, 75, 65),
        M.STEEL: (70, 100, 90, 72, 78, 85, 76, 85, 60, 55, 75, 90),
        M.LEAD: (25, 100, 70, 95, 12, 35, 10, 30, 5, 45, 98, 5),
        M.SILVER: (52, 100, 82, 75, 28, 50, 26, 45, 25, 95, 78, 30),
        M.GOLD: (55, 100, 88, 98, 20, 50, 18, 45, 20, 85, 99, 15),
        M.GLASS: (60, 100, 95, 45, 45, 8, 50, 15, 0, 15, 48, 85),
        M.CRYSTAL: (75, 100, 100, 45, 65, 20, 68, 30, 0, 30, 46, 70),
        M.GEMS: (90, 100, 100, 50, 80, 30, 85, 40, 0, 50, 52, 50),
        M.AMBER: (20, 30, 40, 18, 15, 15, 15, 15, 5, 8, 20, 5),
        M.IVORY: (100, 50, 100, 35, 35, 40, 32, 38, 15, 15, 36, 35),
        M.CHITIN: (100, 45, 100, 25, 45, 50, 45, 50, 35, 12, 26, 50),
        M.GREAT_BEAST_TISSUE: (100, 95, 100, 40, 80, 90, 78, 88, 40, 20, 42, 75),
        M.LIVING_WOOD: (100, 70, 100, 28, 40, 75, 35, 70, 80, 12, 28, 30),
        M.STAR_METAL: (95, 100, 100, 65, 92, 95, 92, 95, 50, 70, 68, 95),
        M.SKYSTEEL: (92, 100, 100, 32, 90, 92, 90, 92, 70, 50, 35, 95),
        M.VOID_GLASS: (100, 100, 100, 25, 75, 30, 80, 40, 0, 0, 25, 100),
        M.DIVINE_TISSUE: (100, 98, 100, 45, 60, 98, 55, 95, 90, 20, 46, 40),
        M.MUD_BRICK: (70, 100, 100, 45, 15, 15, 12, 15, 0, 20, 45, 0),
        M.FIRED_BRICK: (85, 100, 100, 50, 35, 25, 25, 25, 0, 25, 50, 0),
        M.DRESSED_STONE: (85, 100, 100, 80, 60, 55, 55, 50, 0, 35, 82, 0),
        M.RUBBLE: (85, 100, 100, 70, 40, 35, 30, 30, 0, 30, 70, 0),
        M.LIME_MORTAR: (75, 100, 100, 55, 30, 30, 25, 30, 0, 25, 55, 0),
        M.HYDRAULIC_CONCRETE: (85, 100, 100, 70, 50, 45, 40, 45, 0, 30, 70, 0),
        M.THATCH: (100, 10, 100, 5, 5, 20, 3, 15, 30, 5, 5, 0),
        M.TILE: (85, 100, 100, 40, 30, 15, 25, 15, 0, 25, 40, 0),
    }
)


def with_physics(material: MaterialSpec) -> MaterialSpec:
    return MaterialSpec(**{**material.__dict__, **dict(zip(PHYSICS_FIELDS, PHYSICS[material.kind], strict=True))})


MATERIALS: MappingProxyType[MaterialKind, MaterialSpec] = MappingProxyType(
    {
        item.kind: with_physics(item)
        for item in (
            spec((M.WOOD, "Wood", F.ORGANIC), (15, 40, 30, 10), (20, 10, 0), (5, 5, 35)),
            spec((M.CALCIFIED_TISSUE, "Calcified tissue", F.ORGANIC), (25, 20, 25, 20), (25, 5, 10), (10, 5, 20)),
            spec((M.HIDE, "Hide", F.ORGANIC), (8, 45, 15, 0), (10, 5, 0), (10, 8, 40)),
            spec((M.LEATHER, "Leather", F.ORGANIC), (15, 55, 15, 0), (10, 5, 0), (15, 15, 25)),
            spec((M.CLOTH, "Cloth", F.ORGANIC), (3, 30, 5, 0), (15, 10, 0), (10, 10, 45)),
            spec((M.STONE, "Stone", F.STONE), (55, 25, 80, 15), (15, 20, 0), (5, 5, 2)),
            spec((M.FLINT, "Flint", F.STONE), (60, 10, 40, 55), (10, 5, 0), (15, 8, 3)),
            spec((M.OBSIDIAN, "Obsidian", F.STONE), (58, 5, 35, 80), (40, 5, 20), (35, 25, 3)),
            spec((M.CLAY, "Clay", F.STONE), (20, 10, 50, 0), (10, 10, 0), (5, 3, 10)),
            spec((M.HALITE, "Halite", F.STONE), (10, 5, 30, 0), (20, 45, 0), (20, 30, 15)),
            spec((M.SULFUR, "Sulfur", F.STONE), (10, 5, 25, 0), (35, 0, 40), (30, 25, 10)),
            worked(spec((M.COPPER, "Copper", F.METAL), (35, 50, 60, 30), (70, 15, 0), (25, 25, 5)), B.METALLURGY, 1),
            worked(spec((M.TIN, "Tin", F.METAL), (20, 40, 55, 15), (45, 10, 0), (45, 30, 5)), B.METALLURGY, 1),
            worked(spec((M.BRONZE, "Bronze", F.METAL), (50, 60, 65, 50), (60, 20, 0), (35, 40, 4)), B.METALLURGY, 2),
            worked(spec((M.IRON, "Iron", F.METAL), (62, 65, 70, 60), (40, 10, 5), (25, 35, 12)), B.METALLURGY, 3),
            worked(spec((M.STEEL, "Steel", F.METAL), (78, 80, 68, 80), (40, 10, 5), (45, 60, 8)), B.METALLURGY, 5),
            worked(spec((M.LEAD, "Lead", F.METAL), (12, 35, 90, 5), (30, 0, 25), (30, 20, 3)), B.METALLURGY, 1),
            worked(spec((M.SILVER, "Silver", F.PRECIOUS), (30, 45, 65, 25), (85, 70, 0), (65, 75, 3)), B.METALLURGY, 2),
            worked(spec((M.GOLD, "Gold", F.PRECIOUS), (22, 50, 95, 15), (90, 60, 10), (80, 95, 0)), B.METALLURGY, 2),
            worked(spec((M.GLASS, "Glass", F.PRECIOUS), (50, 5, 30, 70), (55, 35, 0), (40, 45, 2)), B.METALLURGY, 2),
            spec((M.CRYSTAL, "Crystal", F.PRECIOUS), (70, 15, 30, 60), (95, 50, 10), (70, 80, 1)),
            spec((M.GEMS, "Gems", F.PRECIOUS), (85, 30, 10, 40), (80, 40, 15), (85, 98, 0)),
            spec((M.AMBER, "Amber", F.PRECIOUS), (18, 15, 15, 5), (60, 45, 5), (55, 60, 5)),
            spec((M.IVORY, "Ivory", F.PRECIOUS), (35, 35, 30, 30), (45, 40, 10), (60, 70, 10)),
            spec((M.CHITIN, "Chitin", F.ORGANIC), (45, 45, 20, 45), (20, 0, 20), (40, 35, 15)),
            spec((M.GREAT_BEAST_TISSUE, "Great beast tissue", F.EXOTIC), (80, 85, 35, 70), (75, 30, 30), (90, 95, 2)),
            worked(spec((M.LIVING_WOOD, "Living wood", F.EXOTIC), (40, 75, 25, 25), (80, 70, 0), (75, 70, 0)), B.BIOMANCY, 1),
            worked(spec((M.STAR_METAL, "Star metal", F.EXOTIC), (92, 90, 60, 90), (90, 60, 20), (95, 98, 0)), B.METALLURGY, 5, B.GATE_LORE),
            worked(spec((M.SKYSTEEL, "Skysteel", F.EXOTIC), (90, 88, 30, 92), (85, 50, 10), (92, 97, 0)), B.METALLURGY, 6, B.MAGIC),
            worked(spec((M.VOID_GLASS, "Void glass", F.EXOTIC), (75, 20, 20, 95), (100, 0, 95), (95, 90, 0)), B.FORBIDDEN, 1),
            worked(spec((M.DIVINE_TISSUE, "Divine tissue", F.EXOTIC), (60, 95, 40, 40), (100, 100, 60), (100, 100, 5)), B.FORBIDDEN, 1),
            spec((M.MUD_BRICK, "Mud brick", F.STONE), (15, 10, 45, 0), (10, 5, 0), (2, 2, 30)),
            worked(spec((M.FIRED_BRICK, "Fired brick", F.STONE), (40, 20, 50, 0), (10, 5, 0), (5, 6, 8)), B.ARCHITECTURE, 1),
            worked(spec((M.DRESSED_STONE, "Dressed stone", F.STONE), (60, 30, 85, 0), (15, 20, 0), (10, 12, 2)), B.ARCHITECTURE, 2),
            spec((M.RUBBLE, "Rubble", F.STONE), (35, 20, 75, 0), (10, 5, 0), (2, 2, 12)),
            worked(spec((M.LIME_MORTAR, "Lime mortar", F.STONE), (35, 25, 55, 0), (10, 5, 0), (8, 6, 10)), B.ARCHITECTURE, 2),
            worked(spec((M.HYDRAULIC_CONCRETE, "Hydraulic concrete", F.STONE), (55, 35, 70, 0), (10, 5, 0), (20, 15, 1)), B.ARCHITECTURE, 3),
            spec((M.THATCH, "Thatch", F.ORGANIC), (2, 15, 5, 0), (10, 5, 0), (2, 1, 50)),
            worked(spec((M.TILE, "Tile", F.STONE), (35, 10, 40, 0), (10, 5, 0), (8, 6, 6)), B.ARCHITECTURE, 1),
        )
    }
)

BUILD_MATERIALS: MappingProxyType[BuildMaterial, MaterialKind] = MappingProxyType({BuildMaterial.TIMBER: M.WOOD, BuildMaterial.STONE: M.STONE})
METAL_FAMILIES = frozenset({MaterialFamily.METAL, MaterialFamily.PRECIOUS, MaterialFamily.EXOTIC})
WEAPON_MATERIALS = (M.STAR_METAL, M.SKYSTEEL, M.GREAT_BEAST_TISSUE, M.STEEL, M.IRON, M.BRONZE, M.COPPER, M.OBSIDIAN, M.FLINT, M.CALCIFIED_TISSUE, M.WOOD)
ARMOUR_MATERIALS = (M.STAR_METAL, M.SKYSTEEL, M.GREAT_BEAST_TISSUE, M.STEEL, M.IRON, M.BRONZE, M.CHITIN, M.LEATHER, M.HIDE, M.CLOTH)
TOOL_MATERIALS = (M.STEEL, M.IRON, M.BRONZE, M.COPPER, M.FLINT, M.STONE, M.CALCIFIED_TISSUE, M.WOOD)
LUXURY_MATERIALS = (M.GEMS, M.GOLD, M.SILVER, M.IVORY, M.AMBER, M.GLASS, M.CRYSTAL)
COIN_MATERIALS = (M.GOLD, M.SILVER, M.BRONZE, M.COPPER)
ALLOYS: MappingProxyType[MaterialKind, tuple[MaterialKind, ...]] = MappingProxyType({M.BRONZE: (M.COPPER, M.TIN), M.STEEL: (M.IRON,), M.SKYSTEEL: (M.IRON,)})
SPECIES_YIELDS: MappingProxyType[BodyPlan, tuple[MaterialKind, ...]] = MappingProxyType(
    {
        BodyPlan.QUADRUPED: (M.HIDE, M.CALCIFIED_TISSUE),
        BodyPlan.AVIAN: (M.CALCIFIED_TISSUE,),
        BodyPlan.SERPENTINE: (M.HIDE, M.CALCIFIED_TISSUE),
        BodyPlan.INSECTOID: (M.CHITIN,),
        BodyPlan.AQUATIC: (M.CALCIFIED_TISSUE,),
        BodyPlan.ARBOREAL: (M.WOOD,),
        BodyPlan.COLOSSAL: (M.GREAT_BEAST_TISSUE, M.IVORY, M.HIDE),
        BodyPlan.HUMANOID: (M.CALCIFIED_TISSUE,),
    }
)
SPECIES_GOODS: MappingProxyType[BodyPlan, tuple[CommodityKind, ...]] = MappingProxyType(
    {
        BodyPlan.QUADRUPED: (CommodityKind.LIVESTOCK, CommodityKind.MOUNTS),
        BodyPlan.AVIAN: (CommodityKind.LIVESTOCK,),
        BodyPlan.AQUATIC: (CommodityKind.FISH,),
        BodyPlan.INSECTOID: (CommodityKind.CLOTH,),
        BodyPlan.COLOSSAL: (CommodityKind.MOUNTS,),
    }
)

SPECIES_GROUNDS: MappingProxyType[CommodityKind, str] = MappingProxyType(
    {
        CommodityKind.LIVESTOCK: "Herds",
        CommodityKind.MOUNTS: "Mount Herds",
        CommodityKind.FISH: "Fisheries",
        CommodityKind.CLOTH: "Silk Grounds",
    }
)
