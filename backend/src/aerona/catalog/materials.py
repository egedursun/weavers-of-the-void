from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.economy import CommodityKind, MaterialFamily
from aerona.domain.enums.material import MaterialKind
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


MATERIALS: MappingProxyType[MaterialKind, MaterialSpec] = MappingProxyType(
    {
        item.kind: item
        for item in (
            spec((M.WOOD, "Wood", F.ORGANIC), (15, 40, 30, 10), (20, 10, 0), (5, 5, 35)),
            spec((M.BONE, "Bone", F.ORGANIC), (25, 20, 25, 20), (25, 5, 10), (10, 5, 20)),
            spec((M.HIDE, "Hide", F.ORGANIC), (8, 45, 15, 0), (10, 5, 0), (10, 8, 40)),
            spec((M.LEATHER, "Leather", F.ORGANIC), (15, 55, 15, 0), (10, 5, 0), (15, 15, 25)),
            spec((M.CLOTH, "Cloth", F.ORGANIC), (3, 30, 5, 0), (15, 10, 0), (10, 10, 45)),
            spec((M.STONE, "Stone", F.STONE), (55, 25, 80, 15), (15, 20, 0), (5, 5, 2)),
            spec((M.FLINT, "Flint", F.STONE), (60, 10, 40, 55), (10, 5, 0), (15, 8, 3)),
            spec((M.OBSIDIAN, "Obsidian", F.STONE), (58, 5, 35, 80), (40, 5, 20), (35, 25, 3)),
            spec((M.CLAY, "Clay", F.STONE), (20, 10, 50, 0), (10, 10, 0), (5, 3, 10)),
            spec((M.SALT, "Salt", F.STONE), (10, 5, 30, 0), (20, 45, 0), (20, 30, 15)),
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
            spec((M.DRAGONBONE, "Dragonbone", F.EXOTIC), (80, 85, 35, 70), (75, 30, 30), (90, 95, 2)),
            worked(spec((M.LIVING_WOOD, "Living wood", F.EXOTIC), (40, 75, 25, 25), (80, 70, 0), (75, 70, 0)), B.BIOMANCY, 1),
            worked(spec((M.STAR_METAL, "Star metal", F.EXOTIC), (92, 90, 60, 90), (90, 60, 20), (95, 98, 0)), B.METALLURGY, 5, B.GATE_LORE),
            worked(spec((M.SKYSTEEL, "Skysteel", F.EXOTIC), (90, 88, 30, 92), (85, 50, 10), (92, 97, 0)), B.METALLURGY, 6, B.MAGIC),
            worked(spec((M.VOID_GLASS, "Void glass", F.EXOTIC), (75, 20, 20, 95), (100, 0, 95), (95, 90, 0)), B.FORBIDDEN, 1),
            worked(spec((M.GODFLESH, "Godflesh", F.EXOTIC), (60, 95, 40, 40), (100, 100, 60), (100, 100, 5)), B.FORBIDDEN, 1),
        )
    }
)

METAL_FAMILIES = frozenset({MaterialFamily.METAL, MaterialFamily.PRECIOUS, MaterialFamily.EXOTIC})
WEAPON_MATERIALS = (M.STAR_METAL, M.SKYSTEEL, M.DRAGONBONE, M.STEEL, M.IRON, M.BRONZE, M.COPPER, M.OBSIDIAN, M.FLINT, M.BONE, M.WOOD)
ARMOUR_MATERIALS = (M.STAR_METAL, M.SKYSTEEL, M.DRAGONBONE, M.STEEL, M.IRON, M.BRONZE, M.CHITIN, M.LEATHER, M.HIDE, M.CLOTH)
TOOL_MATERIALS = (M.STEEL, M.IRON, M.BRONZE, M.COPPER, M.FLINT, M.STONE, M.BONE, M.WOOD)
LUXURY_MATERIALS = (M.GEMS, M.GOLD, M.SILVER, M.IVORY, M.AMBER, M.GLASS, M.CRYSTAL)
COIN_MATERIALS = (M.GOLD, M.SILVER, M.BRONZE, M.COPPER)
ALLOYS: MappingProxyType[MaterialKind, tuple[MaterialKind, ...]] = MappingProxyType({M.BRONZE: (M.COPPER, M.TIN), M.STEEL: (M.IRON,), M.SKYSTEEL: (M.IRON,)})
SPECIES_YIELDS: MappingProxyType[BodyPlan, tuple[MaterialKind, ...]] = MappingProxyType(
    {
        BodyPlan.QUADRUPED: (M.HIDE, M.BONE),
        BodyPlan.AVIAN: (M.BONE,),
        BodyPlan.SERPENTINE: (M.HIDE, M.BONE),
        BodyPlan.INSECTOID: (M.CHITIN,),
        BodyPlan.AQUATIC: (M.BONE,),
        BodyPlan.ARBOREAL: (M.WOOD,),
        BodyPlan.COLOSSAL: (M.DRAGONBONE, M.IVORY, M.HIDE),
        BodyPlan.HUMANOID: (M.BONE,),
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


def material_label(kind: MaterialKind) -> str:
    return MATERIALS[kind].label
