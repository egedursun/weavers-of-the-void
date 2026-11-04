from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import ArmourType, ShieldType, Tactic, UnitFamily, UnitKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass

F = UnitFamily
K = UnitKind
T = TerrainKind
W = WeatherKind


@dataclass(frozen=True)
class UnitSpec:
    kind: UnitKind
    family: UnitFamily
    label: str
    melee: int
    missile: int
    defence: int
    speed: int
    mass: int
    cost: int
    upkeep: int
    armour: ArmourType = ArmourType.NONE
    shield: ShieldType = ShieldType.NONE
    branch: KnowledgeBranch | None = None
    level: int = 0
    social_class: SocialClass | None = None
    counters_charge: bool = False
    terror: int = 0
    terrain: dict[TerrainKind, float] = field(default_factory=dict)
    flying: bool = False


UNITS: MappingProxyType[UnitKind, UnitSpec] = MappingProxyType(
    {
        spec.kind: spec
        for spec in (
            UnitSpec(K.LEVY, F.INFANTRY, "Levy", 30, 0, 25, 40, 20, 1, 1, ArmourType.NONE, ShieldType.SMALL),
            UnitSpec(K.SPEARMEN, F.INFANTRY, "Spearmen", 45, 0, 45, 40, 25, 2, 1, ArmourType.PADDED, ShieldType.LARGE, counters_charge=True),
            UnitSpec(
                K.HEAVY_INFANTRY,
                F.INFANTRY,
                "Heavy infantry",
                65,
                0,
                65,
                30,
                35,
                4,
                2,
                ArmourType.MAIL,
                ShieldType.LARGE,
                KnowledgeBranch.METALLURGY,
                2,
                SocialClass.WARRIOR,
            ),
            UnitSpec(K.SHIELD_WALL, F.INFANTRY, "Shield wall", 50, 0, 75, 30, 30, 3, 2, ArmourType.MAIL, ShieldType.TOWER, KnowledgeBranch.WARFARE, 1),
            UnitSpec(
                K.PIKEMEN, F.INFANTRY, "Pikemen", 50, 0, 55, 30, 30, 3, 2, ArmourType.PADDED, ShieldType.NONE, KnowledgeBranch.WARFARE, 2, counters_charge=True
            ),
            UnitSpec(K.SKIRMISHERS, F.INFANTRY, "Skirmishers", 30, 30, 25, 60, 15, 2, 1, terrain={T.FOREST: 1.2, T.JUNGLE: 1.2, T.HILLS: 1.1}),
            UnitSpec(
                K.BERSERKERS, F.INFANTRY, "Berserkers", 80, 0, 30, 50, 35, 3, 2, ArmourType.HIDE, ShieldType.SMALL, social_class=SocialClass.WARRIOR, terror=15
            ),
            UnitSpec(K.TEMPLE_GUARD, F.INFANTRY, "Temple guard", 60, 0, 60, 35, 30, 4, 2, ArmourType.SCALE, ShieldType.LARGE, social_class=SocialClass.PRIEST),
            UnitSpec(K.SLINGERS, F.MISSILE, "Slingers", 15, 40, 20, 50, 10, 1, 1),
            UnitSpec(K.ARCHERS, F.MISSILE, "Archers", 20, 55, 25, 45, 10, 2, 1, ArmourType.PADDED),
            UnitSpec(K.CROSSBOWMEN, F.MISSILE, "Crossbowmen", 25, 65, 35, 35, 15, 3, 2, ArmourType.PADDED, ShieldType.LARGE, KnowledgeBranch.METALLURGY, 2),
            UnitSpec(K.HORSE_ARCHERS, F.MOUNTED, "Horse archers", 30, 55, 30, 90, 30, 4, 3, ArmourType.HIDE, terrain={T.STEPPE: 1.3, T.PLAIN: 1.3}),
            UnitSpec(K.JAVELINEERS, F.MISSILE, "Javelineers", 35, 45, 30, 50, 15, 2, 1, ArmourType.HIDE, ShieldType.SMALL),
            UnitSpec(
                K.LIGHT_CAVALRY,
                F.MOUNTED,
                "Light cavalry",
                45,
                10,
                30,
                95,
                50,
                4,
                3,
                ArmourType.PADDED,
                ShieldType.SMALL,
                terrain={T.PLAIN: 1.2, T.STEPPE: 1.2},
            ),
            UnitSpec(
                K.HEAVY_CAVALRY,
                F.MOUNTED,
                "Heavy cavalry",
                75,
                0,
                60,
                70,
                90,
                7,
                4,
                ArmourType.PLATE,
                ShieldType.LARGE,
                KnowledgeBranch.METALLURGY,
                3,
                SocialClass.NOBLE,
                terrain={T.PLAIN: 1.3},
            ),
            UnitSpec(K.BEAST_RIDERS, F.MOUNTED, "Beast riders", 60, 10, 45, 70, 80, 6, 4, ArmourType.HIDE, terrain={T.DESERT: 1.2}),
            UnitSpec(
                K.CHARIOTS,
                F.MOUNTED,
                "Chariots",
                65,
                20,
                40,
                80,
                85,
                6,
                4,
                ArmourType.SCALE,
                branch=KnowledgeBranch.METALLURGY,
                level=1,
                terrain={T.PLAIN: 1.2, T.HILLS: 0.6},
            ),
            UnitSpec(K.WAR_BEASTS, F.BEAST, "War beasts", 70, 0, 50, 60, 100, 6, 5, terror=25),
            UnitSpec(K.BOUND_BEASTS, F.BEAST, "Bound beasts", 90, 0, 70, 60, 120, 10, 6, terror=40),
            UnitSpec(K.SKY_MOUNTS, F.BEAST, "Sky mounts", 60, 30, 40, 120, 60, 9, 6, terror=20, flying=True),
            UnitSpec(K.SAPPERS, F.ENGINEER, "Sappers", 20, 0, 30, 35, 10, 3, 2, branch=KnowledgeBranch.ARCHITECTURE, level=1),
            UnitSpec(K.SIEGE_ENGINES, F.ENGINEER, "Siege engines", 0, 70, 20, 15, 0, 8, 4, branch=KnowledgeBranch.ARCHITECTURE, level=2),
            UnitSpec(K.WAR_MAGES, F.MAGIC, "War mages", 20, 70, 30, 40, 5, 9, 5, branch=KnowledgeBranch.MAGIC, level=2, terror=10),
            UnitSpec(K.PRIESTS, F.MAGIC, "Battle priests", 15, 10, 25, 40, 5, 4, 2, social_class=SocialClass.PRIEST),
            UnitSpec(K.NECROMANCERS, F.MAGIC, "Necromancers", 15, 40, 25, 40, 5, 10, 6, branch=KnowledgeBranch.FORBIDDEN, level=1, terror=30),
            UnitSpec(K.GALLEYS, F.NAVAL, "Galleys", 40, 20, 40, 60, 70, 8, 4, branch=KnowledgeBranch.SEAFARING, level=1),
            UnitSpec(K.LONGSHIPS, F.NAVAL, "Longships", 55, 10, 35, 75, 50, 6, 3, branch=KnowledgeBranch.SEAFARING, level=1),
            UnitSpec(K.WARSHIPS, F.NAVAL, "Warships", 50, 50, 60, 55, 90, 12, 6, branch=KnowledgeBranch.SHIPBUILDING, level=2),
            UnitSpec(K.FIRE_SHIPS, F.NAVAL, "Fire ships", 80, 0, 10, 60, 60, 5, 2, branch=KnowledgeBranch.SEAFARING, level=2),
            UnitSpec(K.SKYSHIPS, F.NAVAL, "Skyships", 40, 60, 40, 110, 50, 15, 8, branch=KnowledgeBranch.SKY_NAVIGATION, level=1, flying=True),
            UnitSpec(K.GOLEMS, F.EXOTIC, "Golems", 85, 0, 90, 25, 110, 14, 2, ArmourType.ENCHANTED, branch=KnowledgeBranch.MAGIC, level=3, terror=30),
            UnitSpec(K.VOID_SPAWN, F.EXOTIC, "Void spawn", 75, 20, 50, 60, 60, 10, 4, terror=50),
            UnitSpec(K.GHOST_HOST, F.EXOTIC, "Ghost host", 55, 0, 80, 70, 10, 10, 1, terror=45),
        )
    }
)

ARMOUR_DEFENCE = MappingProxyType(
    {ArmourType.NONE: 0, ArmourType.HIDE: 8, ArmourType.PADDED: 12, ArmourType.MAIL: 22, ArmourType.SCALE: 26, ArmourType.PLATE: 35, ArmourType.ENCHANTED: 45}
)
ARMOUR_WEIGHT = MappingProxyType(
    {ArmourType.NONE: 0, ArmourType.HIDE: 1, ArmourType.PADDED: 1, ArmourType.MAIL: 2, ArmourType.SCALE: 3, ArmourType.PLATE: 4, ArmourType.ENCHANTED: 1}
)
SHIELD_DEFENCE = MappingProxyType({ShieldType.NONE: 0, ShieldType.SMALL: 6, ShieldType.LARGE: 12, ShieldType.TOWER: 18})

TERRAIN_EFFECTS: MappingProxyType[TerrainKind, dict[UnitFamily, float]] = MappingProxyType(
    {
        T.PLAIN: {F.MOUNTED: 1.3},
        T.STEPPE: {F.MOUNTED: 1.3},
        T.FOREST: {F.MOUNTED: 0.5, F.MISSILE: 0.6, F.BEAST: 0.8},
        T.JUNGLE: {F.MOUNTED: 0.5, F.MISSILE: 0.6, F.BEAST: 0.8},
        T.HILLS: {F.MOUNTED: 0.8, F.MISSILE: 1.1},
        T.MOUNTAINS: {F.MOUNTED: 0.3, F.ENGINEER: 0.2, F.BEAST: 0.7},
        T.HIGH_PASS: {F.MOUNTED: 0.3, F.ENGINEER: 0.2},
        T.MARSH: {F.MOUNTED: 0.4, F.INFANTRY: 0.8, F.BEAST: 0.6},
        T.DESERT: {F.INFANTRY: 0.9},
        T.TUNDRA: {F.INFANTRY: 0.9, F.MOUNTED: 0.8},
        T.ICE_SHEET: {F.INFANTRY: 0.8, F.MOUNTED: 0.6},
        T.RIVER_VALLEY: {F.MOUNTED: 0.9},
        T.URBAN: {F.MOUNTED: 0.4, F.ENGINEER: 1.2},
        T.UNDERGROUND: {F.MISSILE: 0.3, F.MOUNTED: 0.2},
        T.CRYSTAL_FIELD: {F.MAGIC: 1.4},
        T.FLESH: {F.MAGIC: 1.2, F.BEAST: 1.2},
        T.VOID_SHORE: {F.EXOTIC: 1.4, F.MAGIC: 1.2},
        T.CANYON: {F.MOUNTED: 0.6, F.MISSILE: 1.2},
        T.RUIN_FIELD: {F.MOUNTED: 0.7},
        T.VOLCANIC: {F.INFANTRY: 0.9},
    }
)
DEFENDER_TERRAIN = MappingProxyType({T.HILLS: 1.2, T.MOUNTAINS: 1.5, T.HIGH_PASS: 1.5, T.URBAN: 1.3, T.RIVER_VALLEY: 1.15, T.CANYON: 1.3})
AMBUSH_TERRAIN = frozenset({T.FOREST, T.JUNGLE, T.MARSH, T.CANYON})
WEATHER_EFFECTS: MappingProxyType[WeatherKind, dict[UnitFamily, float]] = MappingProxyType(
    {
        W.RAIN: {F.MISSILE: 0.75, F.MOUNTED: 0.9},
        W.DOWNPOUR: {F.MISSILE: 0.5, F.MOUNTED: 0.7},
        W.STORM: {F.MISSILE: 0.5, F.MOUNTED: 0.7, F.NAVAL: 0.6},
        W.FOG: {F.MISSILE: 0.4},
        W.SNOW: {F.MISSILE: 0.7, F.MOUNTED: 0.8},
        W.BLIZZARD: {F.MISSILE: 0.5, F.MOUNTED: 0.6, F.INFANTRY: 0.8},
        W.HEAT_WAVE: {F.INFANTRY: 0.85, F.MOUNTED: 0.85},
        W.SANDSTORM: {F.MISSILE: 0.4},
        W.HAIL: {F.MISSILE: 0.7},
        W.MAGIC_STORM: {F.MAGIC: 1.5},
        W.ASH_FALL: {F.MISSILE: 0.7},
        W.VOID_RAIN: {F.EXOTIC: 1.3},
        W.ECLIPSE_DARK: {F.MISSILE: 0.6},
    }
)
BURROWERS = frozenset({K.SAPPERS, K.VOID_SPAWN})
WEAPON_EDGE = MappingProxyType({"blunt": 100, "pike": 70, "crossbow": 90, "spear": 40, "bow": 30, "blade": 20, "claw": 30, "staff": 10, "sling": 50})
FAMILY_WEAPONS: MappingProxyType[UnitFamily, tuple[str, ...]] = MappingProxyType(
    {
        F.INFANTRY: ("spear", "blade", "blunt"),
        F.MISSILE: ("bow", "crossbow", "sling", "blade"),
        F.MOUNTED: ("spear", "blade", "bow"),
        F.BEAST: ("claw",),
        F.ENGINEER: ("blunt",),
        F.MAGIC: ("staff",),
        F.NAVAL: ("spear", "bow"),
        F.EXOTIC: ("claw",),
    }
)
KIND_WEAPONS = MappingProxyType(
    {
        K.PIKEMEN: ("pike", "blade"),
        K.SPEARMEN: ("spear", "blade"),
        K.SHIELD_WALL: ("spear", "blade"),
        K.HEAVY_INFANTRY: ("blade", "blunt"),
        K.BERSERKERS: ("blunt", "blade"),
        K.ARCHERS: ("bow", "blade"),
        K.HORSE_ARCHERS: ("bow", "blade"),
        K.CROSSBOWMEN: ("crossbow", "blade"),
        K.SLINGERS: ("sling",),
        K.JAVELINEERS: ("spear",),
        K.HEAVY_CAVALRY: ("spear", "blade"),
        K.LIGHT_CAVALRY: ("spear", "blade"),
    }
)
HEAVY_WEATHER = frozenset({W.HEAT_WAVE, W.SNOW, W.BLIZZARD})
OMEN_WEATHER = frozenset({W.STORM, W.ECLIPSE_DARK, W.MAGIC_STORM, W.AURORA})

TACTIC_COUNTERS: MappingProxyType[Tactic, frozenset[Tactic]] = MappingProxyType(
    {
        Tactic.HOLD_LINE: frozenset({Tactic.FRONTAL_ASSAULT, Tactic.WEDGE}),
        Tactic.FRONTAL_ASSAULT: frozenset({Tactic.SKIRMISH_HARASS, Tactic.MISSILE_ATTRITION}),
        Tactic.DOUBLE_ENVELOPMENT: frozenset({Tactic.FRONTAL_ASSAULT, Tactic.WEDGE, Tactic.HOLD_LINE}),
        Tactic.FEIGNED_RETREAT: frozenset({Tactic.FRONTAL_ASSAULT, Tactic.WEDGE}),
        Tactic.FLANK_CAVALRY: frozenset({Tactic.HOLD_LINE, Tactic.MISSILE_ATTRITION, Tactic.SHIELD_WALL}),
        Tactic.MISSILE_ATTRITION: frozenset({Tactic.SHIELD_WALL, Tactic.HOLD_LINE, Tactic.RIVER_DEFENCE}),
        Tactic.SHIELD_WALL: frozenset({Tactic.FRONTAL_ASSAULT, Tactic.FLANK_CAVALRY}),
        Tactic.WEDGE: frozenset({Tactic.SHIELD_WALL, Tactic.SKIRMISH_HARASS}),
        Tactic.NIGHT_RAID: frozenset({Tactic.HOLD_LINE, Tactic.SIEGE_ASSAULT}),
        Tactic.AMBUSH: frozenset({Tactic.FRONTAL_ASSAULT, Tactic.FLANK_CAVALRY, Tactic.WEDGE}),
        Tactic.SKIRMISH_HARASS: frozenset({Tactic.HOLD_LINE, Tactic.SHIELD_WALL}),
        Tactic.RIVER_DEFENCE: frozenset({Tactic.FRONTAL_ASSAULT, Tactic.FLANK_CAVALRY}),
        Tactic.SIEGE_ASSAULT: frozenset({Tactic.HOLD_LINE}),
    }
)
TACTIC_TERRAIN: MappingProxyType[Tactic, frozenset[TerrainKind]] = MappingProxyType(
    {
        Tactic.FLANK_CAVALRY: frozenset({T.PLAIN, T.STEPPE, T.DESERT}),
        Tactic.FEIGNED_RETREAT: frozenset({T.PLAIN, T.STEPPE}),
        Tactic.AMBUSH: AMBUSH_TERRAIN,
        Tactic.RIVER_DEFENCE: frozenset({T.RIVER_VALLEY}),
        Tactic.SHIELD_WALL: frozenset({T.PLAIN, T.HILLS, T.HIGH_PASS, T.COAST}),
        Tactic.MISSILE_ATTRITION: frozenset({T.HILLS, T.PLAIN, T.CANYON}),
        Tactic.DOUBLE_ENVELOPMENT: frozenset({T.PLAIN, T.STEPPE}),
    }
)
STYLE_UNITS = MappingProxyType(
    {
        "shieldwall": (K.SHIELD_WALL, K.SPEARMEN, K.ARCHERS),
        "horse_archer": (K.HORSE_ARCHERS, K.LIGHT_CAVALRY, K.SPEARMEN),
        "skirmisher": (K.SKIRMISHERS, K.JAVELINEERS, K.SLINGERS),
        "chariot": (K.CHARIOTS, K.ARCHERS, K.SPEARMEN),
        "phalanx": (K.PIKEMEN, K.HEAVY_INFANTRY, K.SLINGERS),
        "berserker": (K.BERSERKERS, K.LEVY, K.JAVELINEERS),
        "naval_raider": (K.LONGSHIPS, K.SPEARMEN, K.ARCHERS),
        "siege_engineer": (K.HEAVY_INFANTRY, K.SIEGE_ENGINES, K.SAPPERS, K.CROSSBOWMEN),
        "war_magic": (K.WAR_MAGES, K.SPEARMEN, K.ARCHERS),
        "beast_war": (K.WAR_BEASTS, K.BEAST_RIDERS, K.SKIRMISHERS),
    }
)
STYLE_TACTICS = MappingProxyType(
    {
        "shieldwall": (Tactic.SHIELD_WALL, Tactic.HOLD_LINE, Tactic.FRONTAL_ASSAULT),
        "horse_archer": (Tactic.FEIGNED_RETREAT, Tactic.SKIRMISH_HARASS, Tactic.FLANK_CAVALRY),
        "skirmisher": (Tactic.SKIRMISH_HARASS, Tactic.AMBUSH, Tactic.MISSILE_ATTRITION),
        "chariot": (Tactic.FLANK_CAVALRY, Tactic.FRONTAL_ASSAULT),
        "phalanx": (Tactic.HOLD_LINE, Tactic.FRONTAL_ASSAULT, Tactic.DOUBLE_ENVELOPMENT),
        "berserker": (Tactic.FRONTAL_ASSAULT, Tactic.WEDGE, Tactic.NIGHT_RAID),
        "naval_raider": (Tactic.NIGHT_RAID, Tactic.AMBUSH, Tactic.FRONTAL_ASSAULT),
        "siege_engineer": (Tactic.SIEGE_ASSAULT, Tactic.MISSILE_ATTRITION, Tactic.HOLD_LINE),
        "war_magic": (Tactic.MISSILE_ATTRITION, Tactic.HOLD_LINE),
        "beast_war": (Tactic.WEDGE, Tactic.AMBUSH, Tactic.FLANK_CAVALRY),
    }
)
