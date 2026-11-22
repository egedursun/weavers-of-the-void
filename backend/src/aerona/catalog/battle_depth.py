from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.military import Formation, UnitFamily, UnitKind

K = UnitKind
F = UnitFamily


@dataclass(frozen=True)
class WeaponProfile:
    reach: int
    volleys: int
    accuracy: int
    piercing: int


@dataclass(frozen=True)
class FormationSpec:
    label: str
    melee_pct: int
    defence_pct: int
    missile_taken_pct: int
    charge_taken_pct: int
    charge_pct: int
    organisation_loss_pct: int


WEAPON_PROFILES = total(
    UnitKind,
    {
        K.LEVY: WeaponProfile(0, 0, 30, 10),
        K.LINE_INFANTRY: WeaponProfile(1, 0, 45, 30),
        K.HEAVY_INFANTRY: WeaponProfile(0, 0, 55, 40),
        K.SHIELD_INFANTRY: WeaponProfile(0, 0, 50, 25),
        K.PIKE_INFANTRY: WeaponProfile(2, 0, 50, 45),
        K.LIGHT_INFANTRY: WeaponProfile(2, 2, 45, 15),
        K.SHOCK_INFANTRY: WeaponProfile(0, 0, 50, 35),
        K.GUARD_INFANTRY: WeaponProfile(0, 0, 55, 40),
        K.SLINGERS: WeaponProfile(3, 3, 45, 35),
        K.ARCHERS: WeaponProfile(4, 3, 55, 30),
        K.CROSSBOW_INFANTRY: WeaponProfile(4, 2, 65, 75),
        K.MOUNTED_ARCHERS: WeaponProfile(3, 3, 50, 25),
        K.JAVELINEERS: WeaponProfile(2, 2, 50, 40),
        K.LIGHT_CAVALRY: WeaponProfile(1, 1, 40, 20),
        K.HEAVY_CAVALRY: WeaponProfile(1, 0, 55, 55),
        K.BEAST_RIDERS: WeaponProfile(1, 0, 45, 40),
        K.CHARIOTS: WeaponProfile(2, 1, 40, 35),
        K.WAR_BEASTS: WeaponProfile(0, 0, 40, 50),
        K.BOUND_BEASTS: WeaponProfile(0, 0, 45, 70),
        K.SKY_RIDERS: WeaponProfile(1, 1, 45, 45),
        K.SAPPERS: WeaponProfile(0, 0, 35, 50),
        K.SIEGE_CREW: WeaponProfile(5, 1, 35, 90),
        K.BATTLE_CASTERS: WeaponProfile(4, 2, 60, 85),
        K.SUPPORT_CASTERS: WeaponProfile(0, 0, 35, 20),
        K.SUMMONERS: WeaponProfile(3, 1, 50, 70),
        K.GIFTED: WeaponProfile(3, 1, 55, 70),
        K.DAMPENERS: WeaponProfile(1, 1, 40, 30),
        K.DETECTORS: WeaponProfile(1, 1, 30, 20),
        K.NAVAL_CREW: WeaponProfile(3, 2, 40, 40),
        K.SKY_CREW: WeaponProfile(4, 2, 50, 60),
        K.VOID_CREW: WeaponProfile(4, 2, 50, 60),
        K.CONSTRUCTS: WeaponProfile(0, 0, 45, 80),
        K.SUMMONED_HOST: WeaponProfile(1, 0, 45, 65),
        K.MARINES: WeaponProfile(1, 1, 45, 30),
        K.GUNNERS: WeaponProfile(3, 2, 60, 80),
        K.GRENADIERS: WeaponProfile(2, 1, 50, 60),
        K.MOUNTED_GUNNERS: WeaponProfile(3, 2, 55, 70),
        K.VEHICLE_CREW: WeaponProfile(2, 1, 45, 45),
        K.ARTILLERY_CREW: WeaponProfile(6, 1, 50, 95),
        K.ENGINEERS: WeaponProfile(0, 0, 35, 40),
        K.MECHANISED_INFANTRY: WeaponProfile(4, 3, 60, 75),
        K.SPECIAL_FORCES: WeaponProfile(4, 3, 70, 80),
        K.PARTISANS: WeaponProfile(3, 2, 45, 55),
        K.PEACEKEEPERS: WeaponProfile(2, 1, 50, 50),
        K.MEDICS: WeaponProfile(0, 0, 30, 20),
        K.DRONE_OPERATORS: WeaponProfile(8, 2, 70, 85),
        K.SIGNALS_TROOPS: WeaponProfile(3, 1, 50, 60),
        K.POWERED_TROOPERS: WeaponProfile(4, 3, 65, 95),
        K.DROP_TROOPS: WeaponProfile(4, 3, 60, 80),
        K.PILOTS: WeaponProfile(9, 3, 70, 90),
    },
)

BASE_DISCIPLINE = total(
    UnitKind,
    {
        K.LEVY: 20,
        K.LINE_INFANTRY: 40,
        K.HEAVY_INFANTRY: 60,
        K.SHIELD_INFANTRY: 65,
        K.PIKE_INFANTRY: 60,
        K.LIGHT_INFANTRY: 35,
        K.SHOCK_INFANTRY: 25,
        K.GUARD_INFANTRY: 70,
        K.SLINGERS: 30,
        K.ARCHERS: 45,
        K.CROSSBOW_INFANTRY: 50,
        K.MOUNTED_ARCHERS: 50,
        K.JAVELINEERS: 35,
        K.LIGHT_CAVALRY: 45,
        K.HEAVY_CAVALRY: 65,
        K.BEAST_RIDERS: 40,
        K.CHARIOTS: 45,
        K.WAR_BEASTS: 15,
        K.BOUND_BEASTS: 30,
        K.SKY_RIDERS: 50,
        K.SAPPERS: 45,
        K.SIEGE_CREW: 50,
        K.BATTLE_CASTERS: 55,
        K.SUPPORT_CASTERS: 55,
        K.SUMMONERS: 50,
        K.GIFTED: 55,
        K.DAMPENERS: 50,
        K.DETECTORS: 45,
        K.NAVAL_CREW: 50,
        K.SKY_CREW: 60,
        K.VOID_CREW: 60,
        K.CONSTRUCTS: 95,
        K.SUMMONED_HOST: 60,
        K.MARINES: 50,
        K.GUNNERS: 55,
        K.GRENADIERS: 55,
        K.MOUNTED_GUNNERS: 55,
        K.VEHICLE_CREW: 55,
        K.ARTILLERY_CREW: 60,
        K.ENGINEERS: 50,
        K.MECHANISED_INFANTRY: 60,
        K.SPECIAL_FORCES: 85,
        K.PARTISANS: 35,
        K.PEACEKEEPERS: 65,
        K.MEDICS: 55,
        K.DRONE_OPERATORS: 60,
        K.SIGNALS_TROOPS: 60,
        K.POWERED_TROOPERS: 80,
        K.DROP_TROOPS: 75,
        K.PILOTS: 70,
    },
)

FORMATIONS = total(
    Formation,
    {
        Formation.LINE: FormationSpec("Line", 100, 100, 100, 100, 100, 100),
        Formation.COLUMN: FormationSpec("Column", 85, 85, 120, 130, 90, 120),
        Formation.WEDGE: FormationSpec("Wedge", 115, 90, 110, 110, 125, 110),
        Formation.SQUARE: FormationSpec("Square", 90, 115, 135, 50, 60, 90),
        Formation.LOOSE: FormationSpec("Loose order", 80, 85, 60, 140, 70, 115),
        Formation.SHIELDWALL: FormationSpec("Shield wall", 90, 130, 70, 80, 70, 80),
        Formation.DISPERSED: FormationSpec("Dispersed", 75, 90, 45, 120, 60, 110),
        Formation.ENTRENCHED: FormationSpec("Entrenched", 85, 140, 55, 60, 40, 70),
        Formation.ECHELON: FormationSpec("Echelon", 105, 95, 95, 100, 110, 100),
        Formation.CONVOY: FormationSpec("Convoy", 70, 70, 120, 140, 50, 140),
        Formation.SCREEN: FormationSpec("Screen", 80, 85, 70, 110, 70, 105),
        Formation.LAYERED: FormationSpec("Layered", 95, 120, 70, 85, 80, 90),
    },
)

FAMILY_FORMATION = total(
    UnitFamily,
    {
        F.INFANTRY: Formation.LINE,
        F.MISSILE: Formation.LOOSE,
        F.MOUNTED: Formation.WEDGE,
        F.BEAST: Formation.WEDGE,
        F.ENGINEER: Formation.LOOSE,
        F.MAGIC: Formation.LOOSE,
        F.VEHICLE: Formation.LINE,
        F.EXOTIC: Formation.LINE,
        F.AIR: Formation.ECHELON,
        F.SPACE: Formation.LAYERED,
        F.ELECTRONIC: Formation.SCREEN,
        F.SPECIAL: Formation.DISPERSED,
    },
)

KIND_FORMATION = {
    K.SHIELD_INFANTRY: Formation.SHIELDWALL,
    K.PIKE_INFANTRY: Formation.SQUARE,
    K.LIGHT_INFANTRY: Formation.LOOSE,
    K.MECHANISED_INFANTRY: Formation.DISPERSED,
    K.PARTISANS: Formation.DISPERSED,
    K.PEACEKEEPERS: Formation.LINE,
    K.ARTILLERY_CREW: Formation.ENTRENCHED,
    K.GUNNERS: Formation.DISPERSED,
}


def formation_for(kind: UnitKind, family: UnitFamily) -> Formation:
    return KIND_FORMATION.get(kind, FAMILY_FORMATION[family])
