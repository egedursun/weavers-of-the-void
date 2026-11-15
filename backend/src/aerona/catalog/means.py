from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.means import ContainerKind, LockKind, NavigationAid, WaterLift, WritingMedium
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.structure import StructureKind


@dataclass(frozen=True)
class MediumSpec:
    label: str
    rot: int
    burns: bool
    bakes: bool
    copies: int
    raw: CommodityKind | None


@dataclass(frozen=True)
class LockSpec:
    label: str
    level: int
    quality: int


@dataclass(frozen=True)
class LiftSpec:
    label: str
    capacity: int
    needs: Technique


@dataclass(frozen=True)
class AidSpec:
    label: str
    needs: Technique
    magnetic: bool


@dataclass(frozen=True)
class BuildingSpec:
    water: int
    made_from: tuple[MaterialKind, ...]
    needs: Technique | None


@dataclass(frozen=True)
class ContainerSpec:
    label: str
    capacity: int
    breakage: int
    sealed: bool
    maker: SkillKind
    raw: CommodityKind


MEDIA = MappingProxyType(
    {
        WritingMedium.CLAY_TABLET: MediumSpec("Clay tablet", 1, False, True, 0, CommodityKind.ORE),
        WritingMedium.WAX_TABLET: MediumSpec("Wax tablet", 6, True, False, 0, None),
        WritingMedium.BARK: MediumSpec("Bark", 5, True, False, 0, CommodityKind.TIMBER),
        WritingMedium.PALM_LEAF: MediumSpec("Palm leaf", 6, True, False, 0, CommodityKind.HERBS),
        WritingMedium.PAPYRUS: MediumSpec("Papyrus", 8, True, False, 1, CommodityKind.HERBS),
        WritingMedium.PARCHMENT: MediumSpec("Parchment", 2, True, False, 0, CommodityKind.LIVESTOCK),
        WritingMedium.PAPER: MediumSpec("Paper", 4, True, False, 2, CommodityKind.TIMBER),
        WritingMedium.METAL_PLATE: MediumSpec("Metal plate", 0, False, False, 0, CommodityKind.ORE),
        WritingMedium.STONE: MediumSpec("Stone", 0, False, False, 0, None),
        WritingMedium.KNOTTED_CORD: MediumSpec("Knotted cord", 5, True, False, 0, None),
    }
)
CASUAL_MEDIA = (WritingMedium.CLAY_TABLET, WritingMedium.WAX_TABLET, WritingMedium.BARK, WritingMedium.PALM_LEAF, WritingMedium.PAPYRUS)

LOCKS = MappingProxyType(
    {
        LockKind.BAR: LockSpec("Bar and bolt", 1, 20),
        LockKind.WARDED: LockSpec("Warded lock", 2, 40),
        LockKind.TUMBLER: LockSpec("Tumbler lock", 4, 60),
        LockKind.WARDED_SEAL: LockSpec("Warded lock with seal", 3, 50),
        LockKind.COMBINATION: LockSpec("Combination lock", 6, 80),
    }
)

LIFTS = MappingProxyType(
    {
        WaterLift.SHADUF: LiftSpec("Shaduf", 1, Technique.IRRIGATION),
        WaterLift.NORIA: LiftSpec("Noria", 3, Technique.TERRACING),
        WaterLift.SCREW: LiftSpec("Water screw", 3, Technique.DRAINAGE),
        WaterLift.CHAIN_PUMP: LiftSpec("Chain pump", 4, Technique.IRON),
        WaterLift.STEAM_PUMP: LiftSpec("Steam pump", 8, Technique.STEAM_POWER),
    }
)
MINE_PUMPS = frozenset({WaterLift.SCREW, WaterLift.CHAIN_PUMP, WaterLift.STEAM_PUMP})

AIDS = MappingProxyType(
    {
        NavigationAid.COMPASS: AidSpec("Compass", Technique.NAVIGATION_STARS, True),
        NavigationAid.ASTROLABE: AidSpec("Astrolabe", Technique.ASTRONOMY_INSTRUMENTS, False),
        NavigationAid.LOG_LINE: AidSpec("Log-line", Technique.SAILING, False),
        NavigationAid.CHARTS: AidSpec("Charts", Technique.CARTOGRAPHY, False),
    }
)

BUILDING: MappingProxyType[MaterialKind, BuildingSpec] = MappingProxyType(
    {
        MaterialKind.MUD_BRICK: BuildingSpec(10, (MaterialKind.CLAY,), None),
        MaterialKind.FIRED_BRICK: BuildingSpec(50, (MaterialKind.CLAY,), None),
        MaterialKind.DRESSED_STONE: BuildingSpec(70, (MaterialKind.STONE,), None),
        MaterialKind.RUBBLE: BuildingSpec(40, (MaterialKind.STONE,), None),
        MaterialKind.WOOD: BuildingSpec(30, (MaterialKind.WOOD,), None),
        MaterialKind.LIME_MORTAR: BuildingSpec(40, (MaterialKind.STONE,), Technique.ARCH),
        MaterialKind.HYDRAULIC_CONCRETE: BuildingSpec(95, (MaterialKind.STONE,), Technique.AQUEDUCT),
        MaterialKind.THATCH: BuildingSpec(10, (), None),
        MaterialKind.TILE: BuildingSpec(60, (MaterialKind.CLAY,), None),
        MaterialKind.GLASS: BuildingSpec(80, (MaterialKind.GLASS,), None),
        MaterialKind.STONE: BuildingSpec(60, (MaterialKind.STONE,), None),
    }
)
WATER_WORKS = frozenset(
    {
        StructureKind.HARBOUR,
        StructureKind.BRIDGE,
        StructureKind.AQUEDUCT,
        StructureKind.CANAL,
        StructureKind.DAM,
        StructureKind.CANAL_LOCK,
        StructureKind.DRY_DOCK,
    }
)

CONTAINERS = MappingProxyType(
    {
        ContainerKind.AMPHORA: ContainerSpec("Amphora", 2, 8, True, SkillKind.POTTERY, CommodityKind.ORE),
        ContainerKind.BARREL: ContainerSpec("Barrel", 3, 3, True, SkillKind.CARPENTRY, CommodityKind.TIMBER),
        ContainerKind.SACK: ContainerSpec("Sack", 2, 6, False, SkillKind.WEAVING, CommodityKind.CLOTH),
        ContainerKind.CRATE: ContainerSpec("Crate", 3, 4, False, SkillKind.CARPENTRY, CommodityKind.TIMBER),
        ContainerKind.JAR: ContainerSpec("Jar", 1, 10, True, SkillKind.POTTERY, CommodityKind.ORE),
        ContainerKind.CHEST: ContainerSpec("Chest", 2, 2, False, SkillKind.CARPENTRY, CommodityKind.TIMBER),
    }
)
