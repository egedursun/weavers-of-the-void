from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.means import ContainerKind, LockKind, NavigationAid, WaterLift, WritingMedium
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.urban import CargoClass
from aerona.rules.model import keyed
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class MediumSpec:
    label: str
    durability_rule: str
    burns: bool
    bakes: bool
    copies: int
    raw: CommodityKind | None
    needs: Technique | None = None
    networked: bool = False
    divination: bool = False
    bulk: int = 1


@dataclass(frozen=True)
class LockSpec:
    label: str
    level: int
    picked: bool
    needs: tuple[Technique, ...]
    opened_by: tuple[SkillKind, ...]
    fails_in_outage: bool
    difficulty: str


@dataclass(frozen=True)
class LiftSpec:
    label: str
    capacity: int
    needs: Technique
    share: str
    wind: bool = False
    electric: bool = False


@dataclass(frozen=True)
class AidSpec:
    label: str
    needs: Technique | None
    magnetic: bool
    loss_rule: str
    skilled: bool = False
    shore_works: bool = False
    networked: bool = False


@dataclass(frozen=True)
class BuildingSpec:
    water: int
    made_from: tuple[MaterialKind, ...]
    needs: Technique | None


@dataclass(frozen=True)
class ContainerSpec:
    label: str
    breakage: int
    sealed: bool
    maker: SkillKind
    raw: CommodityKind
    suits: frozenset[CargoClass] = frozenset()


MEDIA = total(
    WritingMedium,
    {
        WritingMedium.CLAY_TABLET: MediumSpec("Clay tablet", "clay_tablet_durability", False, True, 0, CommodityKind.ORE, bulk=3),
        WritingMedium.WAX_TABLET: MediumSpec("Wax tablet", "wax_tablet_durability", True, False, 0, None),
        WritingMedium.BARK: MediumSpec("Bark", "bark_durability", True, False, 0, CommodityKind.TIMBER),
        WritingMedium.PALM_LEAF: MediumSpec("Palm leaf", "palm_leaf_durability", True, False, 0, CommodityKind.HERBS),
        WritingMedium.PAPYRUS: MediumSpec("Papyrus", "papyrus_durability", True, False, 1, CommodityKind.HERBS),
        WritingMedium.PARCHMENT: MediumSpec("Parchment", "parchment_durability", True, False, 0, CommodityKind.LIVESTOCK),
        WritingMedium.PAPER: MediumSpec("Paper", "paper_durability", True, False, 2, CommodityKind.TIMBER, needs=Technique.PAPER),
        WritingMedium.METAL_PLATE: MediumSpec("Metal plate", "metal_plate_durability", False, False, 0, CommodityKind.ORE, bulk=3),
        WritingMedium.STONE: MediumSpec("Stone", "stone_durability", False, False, 0, None, bulk=5),
        WritingMedium.KNOTTED_CORD: MediumSpec("Knotted cord", "knotted_cord_durability", True, False, 0, None),
        WritingMedium.CALCIFIED_TISSUE: MediumSpec(
            "Bone and shell", "calcified_tissue_durability", False, False, 0, CommodityKind.LIVESTOCK, divination=True, bulk=2
        ),
        WritingMedium.SILK: MediumSpec("Silk", "silk_durability", True, False, 1, CommodityKind.CLOTH),
        WritingMedium.WOOD_SLIPS: MediumSpec("Slips of wood or cane", "wood_slips_durability", True, False, 1, CommodityKind.TIMBER, bulk=4),
        WritingMedium.ELECTRONIC: MediumSpec("Electronic record", "electronic_durability", False, False, 5, None, needs=Technique.COMPUTATION, networked=True),
        WritingMedium.CLOTH: MediumSpec("Cloth", "cloth_durability", True, False, 1, CommodityKind.CLOTH),
        WritingMedium.POTSHERD: MediumSpec("Potsherd", "potsherd_durability", False, False, 0, CommodityKind.POTTERY, bulk=2),
    },
)
CASUAL_MEDIA = (WritingMedium.CLAY_TABLET, WritingMedium.WAX_TABLET, WritingMedium.BARK, WritingMedium.PALM_LEAF, WritingMedium.PAPYRUS)

LOCKS: Mapping[LockKind, LockSpec] = total(
    LockKind,
    {
        LockKind.BAR: LockSpec("Bar and bolt", 1, True, (), (), False, "bar_difficulty"),
        LockKind.WARDED: LockSpec("Warded lock", 2, True, (), (), False, "warded_difficulty"),
        LockKind.TUMBLER: LockSpec("Tumbler lock", 4, True, (), (), False, "tumbler_difficulty"),
        LockKind.WARDED_SEAL: LockSpec("Warded lock with seal", 3, True, (), (), False, "warded_seal_difficulty"),
        LockKind.COMBINATION: LockSpec("Combination lock", 6, True, (), (), False, "combination_difficulty"),
        LockKind.WORKED: LockSpec(
            "Lock held by a working", 3, False, (Technique.WARDING,), (SkillKind.RITUAL, SkillKind.SPELLCRAFT), False, "worked_difficulty"
        ),
        LockKind.ELECTRONIC: LockSpec(
            "Electronic lock", 6, False, (Technique.ELECTRICITY,), (SkillKind.ELECTRONICS, SkillKind.COMPUTING), True, "electronic_difficulty"
        ),
        LockKind.LIVING: LockSpec("Living lock", 8, False, (Technique.GENETIC_ENGINEERING,), (), False, "living_difficulty"),
    },
)

LIFTS: Mapping[WaterLift, LiftSpec] = total(
    WaterLift,
    {
        WaterLift.SHADUF: LiftSpec("Shaduf", 1, Technique.IRRIGATION, "shaduf_lift"),
        WaterLift.NORIA: LiftSpec("Noria", 3, Technique.TERRACING, "noria_lift"),
        WaterLift.SCREW: LiftSpec("Water screw", 3, Technique.DRAINAGE, "screw_lift"),
        WaterLift.CHAIN_PUMP: LiftSpec("Chain pump", 4, Technique.IRON, "chain_pump_lift"),
        WaterLift.STEAM_PUMP: LiftSpec("Steam pump", 8, Technique.STEAM_POWER, "steam_pump_lift"),
        WaterLift.WIND_PUMP: LiftSpec("Wind pump", 5, Technique.MACHINE_TOOLS, "wind_pump_lift", wind=True),
        WaterLift.ELECTRIC_PUMP: LiftSpec("Electric pump", 12, Technique.ELECTRICITY, "electric_pump_lift", electric=True),
        WaterLift.ANIMAL_WHEEL: LiftSpec("Animal wheel", 3, Technique.PLOUGH, "animal_wheel_lift"),
    },
)
MINE_PUMPS = frozenset({WaterLift.SCREW, WaterLift.CHAIN_PUMP, WaterLift.STEAM_PUMP, WaterLift.ELECTRIC_PUMP})

AIDS = MappingProxyType(
    {
        NavigationAid.COMPASS: AidSpec("Compass", Technique.NAVIGATION_STARS, True, "compass_loss_cut_pct"),
        NavigationAid.ASTROLABE: AidSpec("Astrolabe", Technique.ASTRONOMY_INSTRUMENTS, False, "astrolabe_loss_cut_pct"),
        NavigationAid.LOG_LINE: AidSpec("Log-line", Technique.SAILING, False, "log_line_loss_cut_pct"),
        NavigationAid.CHARTS: AidSpec("Charts", Technique.CARTOGRAPHY, False, "charts_loss_cut_pct"),
        NavigationAid.SOUNDING_LINE: AidSpec("Sounding line", Technique.SAILING, False, "sounding_line_loss_cut_pct"),
        NavigationAid.WAYFINDING: AidSpec("Wayfinding lore", None, False, "wayfinding_loss_cut_pct", skilled=True),
        NavigationAid.BEACONS: AidSpec("Beacons on the shore", None, False, "beacons_loss_cut_pct", shore_works=True),
        NavigationAid.POSITIONING: AidSpec("Positioning by network", Technique.COMPUTATION, False, "positioning_loss_cut_pct", networked=True),
        NavigationAid.PILOTS: AidSpec("Pilots who take vessels in", None, False, "pilots_loss_cut_pct", skilled=True, shore_works=True),
        NavigationAid.BUOYS: AidSpec("Buoys", Technique.SAILING, False, "buoys_loss_cut_pct", shore_works=True),
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

BEACON_WORKS = frozenset({StructureKind.LIGHTHOUSE, StructureKind.BEACON})

CONTAINERS = MappingProxyType(
    {
        ContainerKind.AMPHORA: ContainerSpec("Amphora", 8, True, SkillKind.POTTERY, CommodityKind.ORE, frozenset({CargoClass.LIQUID})),
        ContainerKind.BARREL: ContainerSpec(
            "Barrel", 3, True, SkillKind.CARPENTRY, CommodityKind.TIMBER, frozenset({CargoClass.LIQUID, CargoClass.PERISHABLE})
        ),
        ContainerKind.SACK: ContainerSpec("Sack", 6, False, SkillKind.WEAVING, CommodityKind.CLOTH, frozenset({CargoClass.BULK})),
        ContainerKind.CRATE: ContainerSpec("Crate", 4, False, SkillKind.CARPENTRY, CommodityKind.TIMBER, frozenset({CargoClass.FINE, CargoClass.BULK})),
        ContainerKind.JAR: ContainerSpec("Jar", 10, True, SkillKind.POTTERY, CommodityKind.ORE, frozenset({CargoClass.PERISHABLE, CargoClass.LIQUID})),
        ContainerKind.CHEST: ContainerSpec("Chest", 2, False, SkillKind.CARPENTRY, CommodityKind.TIMBER, frozenset({CargoClass.FINE, CargoClass.RELICS})),
        ContainerKind.BALE: ContainerSpec("Bale", 2, False, SkillKind.WEAVING, CommodityKind.FIBRE, frozenset({CargoClass.BULK})),
        ContainerKind.BASKET: ContainerSpec("Basket", 5, False, SkillKind.WEAVING, CommodityKind.FIBRE, frozenset({CargoClass.PERISHABLE})),
        ContainerKind.SKIN: ContainerSpec("Skin", 4, True, SkillKind.WEAVING, CommodityKind.LIVESTOCK, frozenset({CargoClass.LIQUID})),
        ContainerKind.TANK: ContainerSpec(
            "Tank", 1, True, SkillKind.ENGINEERING, CommodityKind.ORE, frozenset({CargoClass.LIQUID, CargoClass.GAS, CargoClass.HAZARDOUS})
        ),
        ContainerKind.CAGE: ContainerSpec("Cage", 3, False, SkillKind.CARPENTRY, CommodityKind.TIMBER, frozenset({CargoClass.LIVESTOCK, CargoClass.LIVING})),
        ContainerKind.NET_BAG: ContainerSpec("Net bag", 7, False, SkillKind.WEAVING, CommodityKind.FIBRE, frozenset({CargoClass.BULK, CargoClass.PERISHABLE})),
    }
)


def container_capacity(rules: Rules, kind: ContainerKind) -> int:
    return keyed(rules.containers, kind.value, "capacity")


def aid_cut(rules: Rules, aid: NavigationAid) -> int:
    return int(getattr(rules.navigation_instruments, AIDS[aid].loss_rule))


NETWORKED_AIDS = tuple(aid for aid, spec in AIDS.items() if spec.networked)
