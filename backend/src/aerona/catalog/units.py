from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.battle_depth import WEAPON_PROFILES, WeaponProfile
from aerona.core.total import total
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.military import ArmourType, ShieldType, Tactic, UnitFamily, UnitKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass

F = UnitFamily
K = UnitKind


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
            UnitSpec(K.LIGHT_INFANTRY, F.INFANTRY, "Light infantry", 30, 30, 25, 60, 15, 2, 1),
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
            UnitSpec(
                K.CROSSBOW_INFANTRY,
                F.MISSILE,
                "Crossbow infantry",
                25,
                65,
                35,
                35,
                15,
                3,
                2,
                ArmourType.PADDED,
                ShieldType.LARGE,
                KnowledgeBranch.METALLURGY,
                2,
            ),
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
            ),
            UnitSpec(K.MOUNTED_ARCHERS, F.MOUNTED, "Mounted archers", 30, 55, 30, 90, 30, 4, 3, ArmourType.HIDE),
            UnitSpec(
                K.MOUNTED_GUNNERS, F.MOUNTED, "Mounted gunners", 35, 65, 30, 85, 30, 5, 3, ArmourType.PADDED, ShieldType.NONE, KnowledgeBranch.METALLURGY, 4
            ),
            UnitSpec(K.BEAST_RIDERS, F.MOUNTED, "Beast riders", 60, 10, 45, 70, 80, 6, 4, ArmourType.HIDE),
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
            UnitSpec(K.GIFTED, F.MAGIC, "Gifted", 20, 45, 30, 40, 5, 12, 6, terror=25),
            UnitSpec(K.DAMPENERS, F.SPECIAL, "Dampeners", 10, 10, 40, 35, 10, 8, 4),
            UnitSpec(K.DETECTORS, F.SPECIAL, "Detectors", 5, 10, 25, 45, 5, 6, 3),
            UnitSpec(K.CONSTRUCTS, F.EXOTIC, "Constructs", 85, 0, 90, 25, 110, 14, 2, ArmourType.ENCHANTED, branch=KnowledgeBranch.MAGIC, level=3, terror=30),
            UnitSpec(K.SUMMONED_HOST, F.EXOTIC, "Summoned host", 60, 10, 65, 65, 35, 10, 2, terror=45),
            UnitSpec(
                K.MECHANISED_INFANTRY,
                F.INFANTRY,
                "Mechanised infantry",
                45,
                60,
                55,
                75,
                45,
                6,
                3,
                ArmourType.BALLISTIC,
                branch=KnowledgeBranch.METALLURGY,
                level=8,
            ),
            UnitSpec(
                K.SPECIAL_FORCES,
                F.SPECIAL,
                "Special forces",
                60,
                60,
                45,
                65,
                20,
                9,
                4,
                ArmourType.BALLISTIC,
                branch=KnowledgeBranch.WARFARE,
                level=4,
            ),
            UnitSpec(
                K.PARTISANS,
                F.INFANTRY,
                "Partisans",
                30,
                30,
                25,
                55,
                15,
                1,
                1,
            ),
            UnitSpec(K.PEACEKEEPERS, F.INFANTRY, "Peacekeepers", 35, 25, 55, 40, 25, 3, 2, ArmourType.BALLISTIC, ShieldType.RIOT, KnowledgeBranch.CIVICS, 3),
            UnitSpec(K.MEDICS, F.SPECIAL, "Medics", 5, 5, 25, 45, 10, 3, 2, branch=KnowledgeBranch.MEDICINE, level=2),
            UnitSpec(K.DRONE_OPERATORS, F.ELECTRONIC, "Drone operators", 0, 75, 25, 40, 5, 9, 4, branch=KnowledgeBranch.SKY_NAVIGATION, level=6),
            UnitSpec(K.SIGNALS_TROOPS, F.ELECTRONIC, "Signals troops", 10, 15, 30, 45, 10, 6, 3, branch=KnowledgeBranch.WARFARE, level=8),
            UnitSpec(
                K.POWERED_TROOPERS,
                F.SPECIAL,
                "Powered troopers",
                90,
                65,
                90,
                50,
                70,
                16,
                6,
                ArmourType.POWERED,
                branch=KnowledgeBranch.METALLURGY,
                level=10,
                terror=15,
                counters_charge=True,
            ),
            UnitSpec(K.DROP_TROOPS, F.SPACE, "Drop troops", 60, 55, 50, 75, 30, 10, 5, ArmourType.BALLISTIC, branch=KnowledgeBranch.VOID_LIVING, level=2),
            UnitSpec(K.PILOTS, F.AIR, "Pilots", 0, 85, 30, 130, 10, 10, 5, branch=KnowledgeBranch.SKY_NAVIGATION, level=4, flying=True),
        )
    },
)

ARMOUR_DEFENCE = total(
    ArmourType,
    {
        ArmourType.NONE: 0,
        ArmourType.HIDE: 8,
        ArmourType.PADDED: 12,
        ArmourType.MAIL: 22,
        ArmourType.SCALE: 26,
        ArmourType.PLATE: 35,
        ArmourType.ENCHANTED: 45,
        ArmourType.BALLISTIC: 30,
        ArmourType.COMPOSITE: 38,
        ArmourType.POWERED: 50,
        ArmourType.FORCE_FIELD: 55,
    },
)
SHIELD_DEFENCE = total(
    ShieldType, {ShieldType.NONE: 0, ShieldType.SMALL: 6, ShieldType.LARGE: 12, ShieldType.TOWER: 18, ShieldType.RIOT: 14, ShieldType.ENERGY: 22}
)

BURROWERS = frozenset({K.SAPPERS, K.SUMMONED_HOST})
WEAPON_EDGE = MappingProxyType(
    {
        "blunt": 100,
        "pike": 70,
        "crossbow": 90,
        "spear": 40,
        "bow": 30,
        "blade": 20,
        "claw": 30,
        "staff": 10,
        "sling": 50,
        "firearm": 95,
        "launcher": 100,
        "beam": 100,
    }
)
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
        F.AIR: ("launcher", "firearm"),
        F.SPACE: ("firearm", "beam", "blade"),
        F.ELECTRONIC: ("launcher", "firearm"),
        F.SPECIAL: ("firearm", "blade"),
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
        K.CROSSBOW_INFANTRY: ("crossbow", "blade"),
        K.SLINGERS: ("sling",),
        K.JAVELINEERS: ("spear",),
        K.HEAVY_CAVALRY: ("spear", "blade"),
        K.LIGHT_CAVALRY: ("spear", "blade"),
        K.GUNNERS: ("firearm", "blade"),
        K.MOUNTED_GUNNERS: ("firearm", "blade"),
        K.GRENADIERS: ("launcher", "firearm"),
        K.ARTILLERY_CREW: ("launcher",),
        K.MECHANISED_INFANTRY: ("firearm", "launcher"),
        K.PARTISANS: ("firearm", "blade", "blunt"),
        K.PEACEKEEPERS: ("firearm", "blunt"),
        K.MEDICS: ("blunt",),
        K.POWERED_TROOPERS: ("beam", "firearm", "blunt"),
        K.DROP_TROOPS: ("firearm", "launcher"),
    }
)

TACTIC_COUNTERS: MappingProxyType[Tactic, frozenset[Tactic]] = total(
    Tactic,
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
        Tactic.AMBUSH: frozenset({Tactic.FRONTAL_ASSAULT, Tactic.FLANK_CAVALRY, Tactic.WEDGE, Tactic.ARMOURED_THRUST}),
        Tactic.SKIRMISH_HARASS: frozenset({Tactic.HOLD_LINE, Tactic.SHIELD_WALL}),
        Tactic.RIVER_DEFENCE: frozenset({Tactic.FRONTAL_ASSAULT, Tactic.FLANK_CAVALRY}),
        Tactic.SIEGE_ASSAULT: frozenset({Tactic.HOLD_LINE}),
        Tactic.FEINT: frozenset({Tactic.HOLD_LINE, Tactic.RIVER_DEFENCE}),
        Tactic.ARTILLERY_BARRAGE: frozenset({Tactic.HOLD_LINE, Tactic.SHIELD_WALL, Tactic.SIEGE_ASSAULT, Tactic.RIVER_DEFENCE}),
        Tactic.ARMOURED_THRUST: frozenset({Tactic.HOLD_LINE, Tactic.FRONTAL_ASSAULT, Tactic.SKIRMISH_HARASS, Tactic.SHIELD_WALL}),
        Tactic.AIR_SUPERIORITY: frozenset({Tactic.ARMOURED_THRUST, Tactic.ARTILLERY_BARRAGE, Tactic.FLANK_CAVALRY, Tactic.DROP_ASSAULT}),
        Tactic.BLOCKADE: frozenset({Tactic.SIEGE_ASSAULT, Tactic.RIVER_DEFENCE, Tactic.HOLD_LINE}),
        Tactic.GUERRILLA: frozenset({Tactic.ARMOURED_THRUST, Tactic.FRONTAL_ASSAULT, Tactic.HOLD_LINE}),
        Tactic.ELECTRONIC_WARFARE: frozenset({Tactic.AIR_SUPERIORITY, Tactic.ARTILLERY_BARRAGE, Tactic.ORBITAL_BOMBARDMENT}),
        Tactic.ORBITAL_BOMBARDMENT: frozenset({Tactic.HOLD_LINE, Tactic.ARMOURED_THRUST, Tactic.ARTILLERY_BARRAGE, Tactic.SIEGE_ASSAULT}),
        Tactic.DROP_ASSAULT: frozenset({Tactic.RIVER_DEFENCE, Tactic.HOLD_LINE, Tactic.ARTILLERY_BARRAGE}),
        Tactic.INFILTRATION: frozenset({Tactic.HOLD_LINE, Tactic.ARTILLERY_BARRAGE, Tactic.ELECTRONIC_WARFARE}),
    },
)
SUCCESSORS: MappingProxyType[UnitKind, UnitKind] = MappingProxyType(
    {
        K.LEVY: K.GUNNERS,
        K.SLINGERS: K.ARCHERS,
        K.ARCHERS: K.GUNNERS,
        K.CROSSBOW_INFANTRY: K.GUNNERS,
        K.JAVELINEERS: K.GRENADIERS,
        K.SHIELD_INFANTRY: K.LINE_INFANTRY,
        K.PIKE_INFANTRY: K.LINE_INFANTRY,
        K.SHOCK_INFANTRY: K.GRENADIERS,
        K.LINE_INFANTRY: K.MECHANISED_INFANTRY,
        K.HEAVY_INFANTRY: K.POWERED_TROOPERS,
        K.MOUNTED_ARCHERS: K.MOUNTED_GUNNERS,
        K.LIGHT_CAVALRY: K.PILOTS,
        K.HEAVY_CAVALRY: K.VEHICLE_CREW,
        K.CHARIOTS: K.VEHICLE_CREW,
        K.SIEGE_CREW: K.ARTILLERY_CREW,
        K.MARINES: K.DROP_TROOPS,
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
        "siege_engineer": (K.HEAVY_INFANTRY, K.SIEGE_CREW, K.SAPPERS, K.CROSSBOW_INFANTRY),
        "war_magic": (K.BATTLE_CASTERS, K.LINE_INFANTRY, K.ARCHERS),
        "beast_war": (K.WAR_BEASTS, K.BEAST_RIDERS, K.LIGHT_INFANTRY),
        "mechanised": (K.MECHANISED_INFANTRY, K.VEHICLE_CREW, K.ARTILLERY_CREW),
        "air_mobile": (K.PILOTS, K.SKY_CREW, K.SPECIAL_FORCES),
        "guerrilla": (K.PARTISANS, K.LIGHT_INFANTRY, K.SPECIAL_FORCES),
        "drone_war": (K.DRONE_OPERATORS, K.SIGNALS_TROOPS, K.MECHANISED_INFANTRY),
        "orbital": (K.DROP_TROOPS, K.VOID_CREW, K.POWERED_TROOPERS),
        "combined_arms": (K.MECHANISED_INFANTRY, K.ARTILLERY_CREW, K.PILOTS, K.MEDICS),
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
        "naval_raider": (Tactic.NIGHT_RAID, Tactic.AMBUSH, Tactic.FRONTAL_ASSAULT, Tactic.BLOCKADE),
        "siege_engineer": (Tactic.SIEGE_ASSAULT, Tactic.MISSILE_ATTRITION, Tactic.HOLD_LINE, Tactic.ARTILLERY_BARRAGE),
        "war_magic": (Tactic.MISSILE_ATTRITION, Tactic.HOLD_LINE),
        "beast_war": (Tactic.WEDGE, Tactic.AMBUSH, Tactic.FLANK_CAVALRY),
        "mechanised": (Tactic.ARMOURED_THRUST, Tactic.ARTILLERY_BARRAGE, Tactic.DOUBLE_ENVELOPMENT),
        "air_mobile": (Tactic.AIR_SUPERIORITY, Tactic.DROP_ASSAULT, Tactic.FLANK_CAVALRY),
        "guerrilla": (Tactic.GUERRILLA, Tactic.AMBUSH, Tactic.INFILTRATION, Tactic.NIGHT_RAID),
        "drone_war": (Tactic.ELECTRONIC_WARFARE, Tactic.ARTILLERY_BARRAGE, Tactic.MISSILE_ATTRITION),
        "orbital": (Tactic.ORBITAL_BOMBARDMENT, Tactic.DROP_ASSAULT, Tactic.ARMOURED_THRUST),
        "combined_arms": (Tactic.ARTILLERY_BARRAGE, Tactic.ARMOURED_THRUST, Tactic.AIR_SUPERIORITY, Tactic.HOLD_LINE),
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
        K.CROSSBOW_INFANTRY: Y.SKIRMISHER,
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
        K.GIFTED: Y.WAR_MAGIC,
        K.DAMPENERS: Y.WAR_MAGIC,
        K.DETECTORS: Y.WAR_MAGIC,
        K.MECHANISED_INFANTRY: Y.MECHANISED,
        K.SPECIAL_FORCES: Y.GUERRILLA,
        K.PARTISANS: Y.GUERRILLA,
        K.PEACEKEEPERS: Y.COMBINED_ARMS,
        K.MEDICS: Y.COMBINED_ARMS,
        K.DRONE_OPERATORS: Y.DRONE_WAR,
        K.SIGNALS_TROOPS: Y.DRONE_WAR,
        K.POWERED_TROOPERS: Y.ORBITAL,
        K.DROP_TROOPS: Y.ORBITAL,
        K.PILOTS: Y.AIR_MOBILE,
    },
)
