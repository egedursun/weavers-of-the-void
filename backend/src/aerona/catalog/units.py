from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.catalog.battle_depth import WEAPON_PROFILES, WeaponProfile
from aerona.core.total import total
from aerona.domain.enums.demography import MartialStyle
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
    profile: WeaponProfile | None = None


UNITS: MappingProxyType[UnitKind, UnitSpec] = total(
    UnitKind,
    {
        spec.kind: spec
        for spec in (
            UnitSpec(K.LEVY, F.INFANTRY, "Levy", 30, 0, 25, 40, 20, 1, 1, ArmourType.NONE, ShieldType.SMALL),
            UnitSpec(K.LINE_INFANTRY, F.INFANTRY, "Line infantry", 45, 0, 45, 40, 25, 2, 1, ArmourType.PADDED, ShieldType.LARGE, counters_charge=True),
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
            UnitSpec(K.SHIELD_INFANTRY, F.INFANTRY, "Shield infantry", 50, 0, 75, 30, 30, 3, 2, ArmourType.MAIL, ShieldType.TOWER, KnowledgeBranch.WARFARE, 1),
            UnitSpec(
                K.PIKE_INFANTRY,
                F.INFANTRY,
                "Pike infantry",
                50,
                0,
                55,
                30,
                30,
                3,
                2,
                ArmourType.PADDED,
                ShieldType.NONE,
                KnowledgeBranch.WARFARE,
                2,
                counters_charge=True,
            ),
            UnitSpec(K.LIGHT_INFANTRY, F.INFANTRY, "Light infantry", 30, 30, 25, 60, 15, 2, 1, terrain={T.FOREST: 1.2, T.JUNGLE: 1.2, T.HILLS: 1.1}),
            UnitSpec(
                K.SHOCK_INFANTRY,
                F.INFANTRY,
                "Shock infantry",
                80,
                0,
                30,
                50,
                35,
                3,
                2,
                ArmourType.HIDE,
                ShieldType.SMALL,
                social_class=SocialClass.WARRIOR,
                terror=15,
            ),
            UnitSpec(K.GUARD_INFANTRY, F.INFANTRY, "Guard infantry", 60, 0, 60, 35, 30, 4, 2, ArmourType.SCALE, ShieldType.LARGE, KnowledgeBranch.WARFARE, 1),
            UnitSpec(K.MARINES, F.INFANTRY, "Marines", 45, 15, 40, 45, 25, 3, 2, ArmourType.PADDED, ShieldType.SMALL, KnowledgeBranch.SEAFARING, 1),
            UnitSpec(K.SLINGERS, F.MISSILE, "Slingers", 15, 40, 20, 50, 10, 1, 1),
            UnitSpec(K.ARCHERS, F.MISSILE, "Archers", 20, 55, 25, 45, 10, 2, 1, ArmourType.PADDED),
            UnitSpec(K.CROSSBOWMEN, F.MISSILE, "Crossbowmen", 25, 65, 35, 35, 15, 3, 2, ArmourType.PADDED, ShieldType.LARGE, KnowledgeBranch.METALLURGY, 2),
            UnitSpec(K.JAVELINEERS, F.MISSILE, "Javelineers", 35, 45, 30, 50, 15, 2, 1, ArmourType.HIDE, ShieldType.SMALL),
            UnitSpec(K.GUNNERS, F.MISSILE, "Gunners", 25, 75, 30, 35, 15, 4, 2, ArmourType.PADDED, ShieldType.NONE, KnowledgeBranch.METALLURGY, 4),
            UnitSpec(
                K.GRENADIERS, F.MISSILE, "Grenadiers", 40, 60, 35, 40, 20, 4, 2, ArmourType.PADDED, ShieldType.NONE, KnowledgeBranch.METALLURGY, 4, terror=10
            ),
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
            UnitSpec(K.MOUNTED_ARCHERS, F.MOUNTED, "Mounted archers", 30, 55, 30, 90, 30, 4, 3, ArmourType.HIDE, terrain={T.STEPPE: 1.3, T.PLAIN: 1.3}),
            UnitSpec(
                K.MOUNTED_GUNNERS, F.MOUNTED, "Mounted gunners", 35, 65, 30, 85, 30, 5, 3, ArmourType.PADDED, ShieldType.NONE, KnowledgeBranch.METALLURGY, 4
            ),
            UnitSpec(K.BEAST_RIDERS, F.MOUNTED, "Beast riders", 60, 10, 45, 70, 80, 6, 4, ArmourType.HIDE, terrain={T.DESERT: 1.2}),
            UnitSpec(K.SKY_RIDERS, F.MOUNTED, "Sky riders", 60, 30, 40, 120, 60, 9, 6, terror=20, flying=True),
            UnitSpec(
                K.CHARIOTS,
                F.VEHICLE,
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
            UnitSpec(K.VEHICLE_CREW, F.VEHICLE, "Vehicle crew", 30, 30, 40, 40, 20, 4, 2, ArmourType.PADDED, branch=KnowledgeBranch.WARFARE, level=2),
            UnitSpec(K.SIEGE_CREW, F.VEHICLE, "Siege crew", 0, 70, 20, 15, 0, 8, 4, branch=KnowledgeBranch.ARCHITECTURE, level=2),
            UnitSpec(K.ARTILLERY_CREW, F.VEHICLE, "Artillery crew", 0, 80, 20, 20, 0, 8, 4, branch=KnowledgeBranch.METALLURGY, level=4),
            UnitSpec(K.NAVAL_CREW, F.VEHICLE, "Naval crew", 40, 30, 40, 55, 40, 4, 2, branch=KnowledgeBranch.SEAFARING, level=1),
            UnitSpec(K.SKY_CREW, F.VEHICLE, "Sky crew", 40, 50, 40, 100, 30, 6, 3, branch=KnowledgeBranch.SKY_NAVIGATION, level=1, flying=True),
            UnitSpec(K.VOID_CREW, F.VEHICLE, "Void crew", 40, 50, 40, 90, 30, 8, 4, branch=KnowledgeBranch.VOID_LIVING, level=1, flying=True),
            UnitSpec(K.WAR_BEASTS, F.BEAST, "War beasts", 70, 0, 50, 60, 100, 6, 5, terror=25),
            UnitSpec(K.BOUND_BEASTS, F.BEAST, "Bound beasts", 90, 0, 70, 60, 120, 10, 6, terror=40),
            UnitSpec(K.SAPPERS, F.ENGINEER, "Sappers", 20, 0, 30, 35, 10, 3, 2, branch=KnowledgeBranch.ARCHITECTURE, level=1),
            UnitSpec(K.ENGINEERS, F.ENGINEER, "Engineers", 20, 0, 35, 35, 10, 3, 2, branch=KnowledgeBranch.ARCHITECTURE, level=2),
            UnitSpec(K.BATTLE_CASTERS, F.MAGIC, "Battle casters", 20, 70, 30, 40, 5, 9, 5, branch=KnowledgeBranch.MAGIC, level=2, terror=10),
            UnitSpec(K.SUPPORT_CASTERS, F.MAGIC, "Support casters", 15, 10, 25, 40, 5, 4, 2, social_class=SocialClass.PRIEST),
            UnitSpec(K.SUMMONERS, F.MAGIC, "Summoners", 15, 40, 25, 40, 5, 10, 6, branch=KnowledgeBranch.MAGIC, level=2, terror=30),
            UnitSpec(K.CONSTRUCTS, F.EXOTIC, "Constructs", 85, 0, 90, 25, 110, 14, 2, ArmourType.ENCHANTED, branch=KnowledgeBranch.MAGIC, level=3, terror=30),
            UnitSpec(K.SUMMONED_HOST, F.EXOTIC, "Summoned host", 60, 10, 65, 65, 35, 10, 2, terror=45),
        )
    },
)

ARMOUR_DEFENCE = MappingProxyType(
    {ArmourType.NONE: 0, ArmourType.HIDE: 8, ArmourType.PADDED: 12, ArmourType.MAIL: 22, ArmourType.SCALE: 26, ArmourType.PLATE: 35, ArmourType.ENCHANTED: 45}
)
SHIELD_DEFENCE = MappingProxyType({ShieldType.NONE: 0, ShieldType.SMALL: 6, ShieldType.LARGE: 12, ShieldType.TOWER: 18})

TERRAIN_EFFECTS: MappingProxyType[TerrainKind, dict[UnitFamily, float]] = MappingProxyType(
    {
        T.PLAIN: {F.MOUNTED: 1.3},
        T.STEPPE: {F.MOUNTED: 1.3},
        T.FOREST: {F.MOUNTED: 0.5, F.MISSILE: 0.6, F.BEAST: 0.8, F.VEHICLE: 0.6},
        T.JUNGLE: {F.MOUNTED: 0.5, F.MISSILE: 0.6, F.BEAST: 0.8, F.VEHICLE: 0.5},
        T.HILLS: {F.MOUNTED: 0.8, F.MISSILE: 1.1},
        T.MOUNTAINS: {F.MOUNTED: 0.3, F.ENGINEER: 0.2, F.BEAST: 0.7, F.VEHICLE: 0.3},
        T.HIGH_PASS: {F.MOUNTED: 0.3, F.ENGINEER: 0.2, F.VEHICLE: 0.2},
        T.MARSH: {F.MOUNTED: 0.4, F.INFANTRY: 0.8, F.BEAST: 0.6, F.VEHICLE: 0.4},
        T.DESERT: {F.INFANTRY: 0.9},
        T.TUNDRA: {F.INFANTRY: 0.9, F.MOUNTED: 0.8},
        T.ICE_SHEET: {F.INFANTRY: 0.8, F.MOUNTED: 0.6},
        T.RIVER_VALLEY: {F.MOUNTED: 0.9},
        T.URBAN: {F.MOUNTED: 0.4, F.ENGINEER: 1.2, F.VEHICLE: 0.8},
        T.UNDERGROUND: {F.MISSILE: 0.3, F.MOUNTED: 0.2, F.VEHICLE: 0.3},
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
        W.STORM: {F.MISSILE: 0.5, F.MOUNTED: 0.7, F.VEHICLE: 0.6},
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
BURROWERS = frozenset({K.SAPPERS, K.SUMMONED_HOST})
WEAPON_EDGE = MappingProxyType({"blunt": 100, "pike": 70, "crossbow": 90, "spear": 40, "bow": 30, "blade": 20, "claw": 30, "staff": 10, "sling": 50})
FAMILY_WEAPONS: MappingProxyType[UnitFamily, tuple[str, ...]] = MappingProxyType(
    {
        F.INFANTRY: ("spear", "blade", "blunt"),
        F.MISSILE: ("bow", "crossbow", "sling", "blade"),
        F.MOUNTED: ("spear", "blade", "bow"),
        F.BEAST: ("claw",),
        F.ENGINEER: ("blunt",),
        F.MAGIC: ("staff",),
        F.VEHICLE: ("spear", "bow"),
        F.EXOTIC: ("claw",),
    }
)
KIND_WEAPONS = MappingProxyType(
    {
        K.PIKE_INFANTRY: ("pike", "blade"),
        K.LINE_INFANTRY: ("spear", "blade"),
        K.SHIELD_INFANTRY: ("spear", "blade"),
        K.HEAVY_INFANTRY: ("blade", "blunt"),
        K.SHOCK_INFANTRY: ("blunt", "blade"),
        K.ARCHERS: ("bow", "blade"),
        K.MOUNTED_ARCHERS: ("bow", "blade"),
        K.CROSSBOWMEN: ("crossbow", "blade"),
        K.SLINGERS: ("sling",),
        K.JAVELINEERS: ("spear",),
        K.HEAVY_CAVALRY: ("spear", "blade"),
        K.LIGHT_CAVALRY: ("spear", "blade"),
    }
)
HEAVY_WEATHER = frozenset({W.HEAT_WAVE, W.SNOW, W.BLIZZARD})

TACTIC_COUNTERS: MappingProxyType[Tactic, frozenset[Tactic]] = MappingProxyType(
    {
        Tactic.HOLD_LINE: frozenset({Tactic.FRONTAL_ASSAULT, Tactic.WEDGE}),
        Tactic.FRONTAL_ASSAULT: frozenset({Tactic.SKIRMISH_HARASS, Tactic.MISSILE_ATTRITION, Tactic.FEINT}),
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
        Tactic.FEINT: frozenset({Tactic.HOLD_LINE, Tactic.RIVER_DEFENCE}),
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
        "shieldwall": (K.SHIELD_INFANTRY, K.LINE_INFANTRY, K.ARCHERS),
        "horse_archer": (K.MOUNTED_ARCHERS, K.LIGHT_CAVALRY, K.LINE_INFANTRY),
        "skirmisher": (K.LIGHT_INFANTRY, K.JAVELINEERS, K.SLINGERS),
        "chariot": (K.CHARIOTS, K.ARCHERS, K.LINE_INFANTRY),
        "phalanx": (K.PIKE_INFANTRY, K.HEAVY_INFANTRY, K.SLINGERS),
        "shock": (K.SHOCK_INFANTRY, K.LEVY, K.JAVELINEERS),
        "naval_raider": (K.NAVAL_CREW, K.LINE_INFANTRY, K.ARCHERS),
        "siege_engineer": (K.HEAVY_INFANTRY, K.SIEGE_CREW, K.SAPPERS, K.CROSSBOWMEN),
        "war_magic": (K.BATTLE_CASTERS, K.LINE_INFANTRY, K.ARCHERS),
        "beast_war": (K.WAR_BEASTS, K.BEAST_RIDERS, K.LIGHT_INFANTRY),
    }
)
STYLE_TACTICS = MappingProxyType(
    {
        "shieldwall": (Tactic.SHIELD_WALL, Tactic.HOLD_LINE, Tactic.FRONTAL_ASSAULT),
        "horse_archer": (Tactic.FEIGNED_RETREAT, Tactic.SKIRMISH_HARASS, Tactic.FLANK_CAVALRY),
        "skirmisher": (Tactic.SKIRMISH_HARASS, Tactic.AMBUSH, Tactic.MISSILE_ATTRITION, Tactic.FEINT),
        "chariot": (Tactic.FLANK_CAVALRY, Tactic.FRONTAL_ASSAULT),
        "phalanx": (Tactic.HOLD_LINE, Tactic.FRONTAL_ASSAULT, Tactic.DOUBLE_ENVELOPMENT, Tactic.FEINT),
        "shock": (Tactic.FRONTAL_ASSAULT, Tactic.WEDGE, Tactic.NIGHT_RAID),
        "naval_raider": (Tactic.NIGHT_RAID, Tactic.AMBUSH, Tactic.FRONTAL_ASSAULT),
        "siege_engineer": (Tactic.SIEGE_ASSAULT, Tactic.MISSILE_ATTRITION, Tactic.HOLD_LINE),
        "war_magic": (Tactic.MISSILE_ATTRITION, Tactic.HOLD_LINE),
        "beast_war": (Tactic.WEDGE, Tactic.AMBUSH, Tactic.FLANK_CAVALRY),
    }
)


def weapon_of(spec: UnitSpec) -> WeaponProfile:
    return spec.profile if spec.profile is not None else WEAPON_PROFILES[spec.kind]


Y = MartialStyle
ROLE_STYLES: MappingProxyType[UnitKind, MartialStyle] = total(
    UnitKind,
    {
        K.LEVY: Y.SHIELDWALL,
        K.LINE_INFANTRY: Y.SHIELDWALL,
        K.GUARD_INFANTRY: Y.SHIELDWALL,
        K.SHIELD_INFANTRY: Y.SHIELDWALL,
        K.HEAVY_INFANTRY: Y.SHOCK,
        K.SHOCK_INFANTRY: Y.SHOCK,
        K.PIKE_INFANTRY: Y.PHALANX,
        K.LIGHT_INFANTRY: Y.SKIRMISHER,
        K.ARCHERS: Y.SKIRMISHER,
        K.CROSSBOWMEN: Y.SKIRMISHER,
        K.SLINGERS: Y.SKIRMISHER,
        K.JAVELINEERS: Y.SKIRMISHER,
        K.GUNNERS: Y.SKIRMISHER,
        K.GRENADIERS: Y.SHOCK,
        K.MARINES: Y.NAVAL_RAIDER,
        K.NAVAL_CREW: Y.NAVAL_RAIDER,
        K.SKY_CREW: Y.NAVAL_RAIDER,
        K.VOID_CREW: Y.NAVAL_RAIDER,
        K.MOUNTED_ARCHERS: Y.HORSE_ARCHER,
        K.MOUNTED_GUNNERS: Y.HORSE_ARCHER,
        K.LIGHT_CAVALRY: Y.HORSE_ARCHER,
        K.HEAVY_CAVALRY: Y.SHOCK,
        K.CHARIOTS: Y.CHARIOT,
        K.BEAST_RIDERS: Y.BEAST_WAR,
        K.SKY_RIDERS: Y.BEAST_WAR,
        K.WAR_BEASTS: Y.BEAST_WAR,
        K.BOUND_BEASTS: Y.BEAST_WAR,
        K.ENGINEERS: Y.SIEGE_ENGINEER,
        K.SAPPERS: Y.SIEGE_ENGINEER,
        K.SIEGE_CREW: Y.SIEGE_ENGINEER,
        K.ARTILLERY_CREW: Y.SIEGE_ENGINEER,
        K.VEHICLE_CREW: Y.SIEGE_ENGINEER,
        K.CONSTRUCTS: Y.WAR_MAGIC,
        K.SUMMONED_HOST: Y.WAR_MAGIC,
        K.BATTLE_CASTERS: Y.WAR_MAGIC,
        K.SUPPORT_CASTERS: Y.WAR_MAGIC,
        K.SUMMONERS: Y.WAR_MAGIC,
    },
)
