from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.military import Formation, MoraleState, UnitFamily, UnitKind

VOLLEYS_CARRIED = 9
K = UnitKind
T = TerrainKind
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
        K.SPEARMEN: WeaponProfile(1, 0, 45, 30),
        K.HEAVY_INFANTRY: WeaponProfile(0, 0, 55, 40),
        K.SHIELD_WALL: WeaponProfile(0, 0, 50, 25),
        K.PIKEMEN: WeaponProfile(2, 0, 50, 45),
        K.SKIRMISHERS: WeaponProfile(2, 2, 45, 15),
        K.BERSERKERS: WeaponProfile(0, 0, 50, 35),
        K.TEMPLE_GUARD: WeaponProfile(0, 0, 55, 40),
        K.SLINGERS: WeaponProfile(3, 3, 45, 35),
        K.ARCHERS: WeaponProfile(4, 3, 55, 30),
        K.CROSSBOWMEN: WeaponProfile(4, 2, 65, 75),
        K.HORSE_ARCHERS: WeaponProfile(3, 3, 50, 25),
        K.JAVELINEERS: WeaponProfile(2, 2, 50, 40),
        K.LIGHT_CAVALRY: WeaponProfile(1, 1, 40, 20),
        K.HEAVY_CAVALRY: WeaponProfile(1, 0, 55, 55),
        K.BEAST_RIDERS: WeaponProfile(1, 0, 45, 40),
        K.CHARIOTS: WeaponProfile(2, 1, 40, 35),
        K.WAR_BEASTS: WeaponProfile(0, 0, 40, 50),
        K.BOUND_BEASTS: WeaponProfile(0, 0, 45, 70),
        K.SKY_MOUNTS: WeaponProfile(1, 1, 45, 45),
        K.SAPPERS: WeaponProfile(0, 0, 35, 50),
        K.SIEGE_ENGINES: WeaponProfile(5, 1, 35, 90),
        K.WAR_MAGES: WeaponProfile(4, 2, 60, 85),
        K.PRIESTS: WeaponProfile(0, 0, 35, 20),
        K.NECROMANCERS: WeaponProfile(3, 1, 50, 70),
        K.GALLEYS: WeaponProfile(3, 2, 40, 40),
        K.LONGSHIPS: WeaponProfile(2, 1, 40, 30),
        K.WARSHIPS: WeaponProfile(4, 2, 50, 60),
        K.FIRE_SHIPS: WeaponProfile(1, 1, 35, 80),
        K.SKYSHIPS: WeaponProfile(4, 2, 50, 60),
        K.GOLEMS: WeaponProfile(0, 0, 45, 80),
        K.VOID_SPAWN: WeaponProfile(1, 0, 45, 65),
        K.GHOST_HOST: WeaponProfile(0, 0, 40, 60),
    },
)

BASE_DISCIPLINE = total(
    UnitKind,
    {
        K.LEVY: 20,
        K.SPEARMEN: 40,
        K.HEAVY_INFANTRY: 60,
        K.SHIELD_WALL: 65,
        K.PIKEMEN: 60,
        K.SKIRMISHERS: 35,
        K.BERSERKERS: 25,
        K.TEMPLE_GUARD: 70,
        K.SLINGERS: 30,
        K.ARCHERS: 45,
        K.CROSSBOWMEN: 50,
        K.HORSE_ARCHERS: 50,
        K.JAVELINEERS: 35,
        K.LIGHT_CAVALRY: 45,
        K.HEAVY_CAVALRY: 65,
        K.BEAST_RIDERS: 40,
        K.CHARIOTS: 45,
        K.WAR_BEASTS: 15,
        K.BOUND_BEASTS: 30,
        K.SKY_MOUNTS: 50,
        K.SAPPERS: 45,
        K.SIEGE_ENGINES: 50,
        K.WAR_MAGES: 55,
        K.PRIESTS: 55,
        K.NECROMANCERS: 50,
        K.GALLEYS: 45,
        K.LONGSHIPS: 50,
        K.WARSHIPS: 60,
        K.FIRE_SHIPS: 40,
        K.SKYSHIPS: 60,
        K.GOLEMS: 95,
        K.VOID_SPAWN: 20,
        K.GHOST_HOST: 80,
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
        F.NAVAL: Formation.LINE,
        F.EXOTIC: Formation.LINE,
    },
)

KIND_FORMATION = {K.SHIELD_WALL: Formation.SHIELDWALL, K.PIKEMEN: Formation.SQUARE, K.SKIRMISHERS: Formation.LOOSE}

TERRAIN_WIDTH = total(
    TerrainKind,
    {
        T.PLAIN: 160,
        T.STEPPE: 180,
        T.FOREST: 70,
        T.JUNGLE: 55,
        T.MARSH: 65,
        T.HILLS: 110,
        T.MOUNTAINS: 50,
        T.HIGH_PASS: 25,
        T.DESERT: 150,
        T.TUNDRA: 130,
        T.ICE_SHEET: 120,
        T.VOLCANIC: 80,
        T.COAST: 120,
        T.ISLAND: 90,
        T.RIVER_VALLEY: 100,
        T.CANYON: 30,
        T.UNDERGROUND: 30,
        T.CRYSTAL_FIELD: 90,
        T.FLESH: 85,
        T.VOID_SHORE: 75,
        T.RUIN_FIELD: 70,
        T.URBAN: 45,
        T.SEA: 140,
    },
)

MORALE_LABELS = total(
    MoraleState,
    {
        MoraleState.STEADY: "Steady",
        MoraleState.SHAKEN: "Shaken",
        MoraleState.WAVERING: "Wavering",
        MoraleState.ROUTING: "Routing",
        MoraleState.BROKEN: "Broken",
        MoraleState.RALLIED: "Rallied",
    },
)


def formation_for(kind: UnitKind, family: UnitFamily) -> Formation:
    return KIND_FORMATION.get(kind, FAMILY_FORMATION[family])
