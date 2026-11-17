from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body import DamageType as D
from aerona.domain.enums.equipment import EquipmentFamily as E
from aerona.domain.enums.records import StepAction as A
from aerona.domain.enums.records import StepState as T
from aerona.domain.enums.vehicles import VehicleDomain as V
from aerona.domain.enums.vehicles import VehicleSection as S

KINETIC = (S.HULL, S.DECK, S.GUN_DECK, S.ARMOUR_PLATING, S.MAST, S.BOW, S.STERN, S.CHASSIS, S.FRAME, S.TURRET, S.HARDPOINT, S.HOLD)
FLAMMABLE = (S.SAILS, S.RIGGING, S.ENVELOPE, S.DECK, S.GONDOLA, S.WINGS, S.CREW_QUARTERS, S.MAST)
CREW_STATIONS = (S.CREW_QUARTERS, S.GUN_DECK, S.BRIDGE, S.COCKPIT, S.TURRET, S.TROOP_BAY, S.MAGAZINE)
POWER_TARGETS = (S.WARD, S.CORE, S.POWER_CORE, S.CREW_QUARTERS, S.BRIDGE)
BELOW_THE_LINE = (S.KEEL, S.HULL, S.BALLAST, S.DRIVE, S.ENGINE, S.RUDDER)

DAMAGE_SECTIONS: MappingProxyType[D, tuple[S, ...]] = total(
    D,
    {
        D.CUT: KINETIC,
        D.PIERCE: KINETIC,
        D.BLUNT: KINETIC,
        D.BALLISTIC: KINETIC,
        D.FIRE: FLAMMABLE,
        D.COLD: (S.RIGGING, S.SAILS, S.ENGINE, S.LIFE_SUPPORT, S.FUEL_STORE),
        D.VENOM: (S.CREW_QUARTERS, S.LIFE_SUPPORT, S.BRIDGE),
        D.CHEMICAL: (S.CREW_QUARTERS, S.LIFE_SUPPORT, S.HULL, S.ENVELOPE),
        D.MAGIC: POWER_TARGETS,
        D.HOLY: POWER_TARGETS,
        D.VOID: POWER_TARGETS,
        D.PSYCHIC: (S.BRIDGE, S.COCKPIT, S.CREW_QUARTERS, S.CORE),
        D.EXPLOSIVE: CREW_STATIONS,
        D.ENERGY: (S.WARD, S.ARMOUR_PLATING, S.HULL, S.LIFE_SUPPORT, S.SENSORS, S.DRIVE),
        D.ELECTRIC: (S.SENSORS, S.NAVIGATION, S.POWER_CORE, S.ENGINE, S.BRIDGE),
        D.RADIATION: (S.CREW_QUARTERS, S.LIFE_SUPPORT, S.COCKPIT),
        D.SONIC: (S.CREW_QUARTERS, S.HULL, S.SENSORS),
    },
)
FAMILY_SECTIONS: MappingProxyType[E, tuple[S, ...]] = MappingProxyType(
    {
        E.TORPEDO: BELOW_THE_LINE,
        E.RAM: BELOW_THE_LINE,
        E.MINE_LAYER: BELOW_THE_LINE,
        E.HARPOON: (S.HULL, S.ENVELOPE, S.GONDOLA, S.WINGS),
        E.BOARDING_GEAR: (S.DECK, S.CREW_QUARTERS),
    }
)
SHIELDED = frozenset({D.ENERGY, D.MAGIC, D.HOLY, D.VOID, D.PSYCHIC, D.ELECTRIC, D.RADIATION, D.SONIC})
WATERBORNE = frozenset({V.WATER, V.UNDERWATER, V.AMPHIBIOUS})
LIFTED = frozenset({V.AIR, V.GAS_GIANT})
WEATHERED = frozenset({V.WATER, V.UNDERWATER, V.AMPHIBIOUS, V.AIR, V.GAS_GIANT})
EVERY_DOMAIN = frozenset(V)
DRY = EVERY_DOMAIN - WATERBORNE


@dataclass(frozen=True)
class ChainSpec:
    action: A
    state: T | None
    domains: frozenset[V] = EVERY_DOMAIN
    lost: bool = False


NO_CHAIN: tuple[ChainSpec, ...] = ()
EXPLODES = (ChainSpec(A.EXPLODE, T.DISABLED, lost=True),)
VENTS = (ChainSpec(A.VENT, T.DEPRESSURISED),)
DIES_DOWN = (ChainSpec(A.LOSE_POWER, T.ADRIFT),)
FALLS = (ChainSpec(A.CRASH, T.GROUNDED, LIFTED),)
HOLED = (ChainSpec(A.FLOOD, T.FLOODING, WATERBORNE), ChainSpec(A.VENT, T.BREACHED, DRY))
UNWARDED = (ChainSpec(A.LOSE_SHIELD, T.UNSHIELDED),)
BURNS = (ChainSpec(A.IGNITE, T.BURNING),)

SECTION_CHAINS: MappingProxyType[S, tuple[ChainSpec, ...]] = total(
    S,
    {
        S.HULL: HOLED,
        S.KEEL: HOLED,
        S.DECK: BURNS,
        S.BOW: HOLED,
        S.STERN: HOLED,
        S.HOLD: HOLED,
        S.CARGO_BAY: NO_CHAIN,
        S.TROOP_BAY: NO_CHAIN,
        S.CREW_QUARTERS: NO_CHAIN,
        S.BRIDGE: NO_CHAIN,
        S.COCKPIT: NO_CHAIN,
        S.MAST: (*FALLS, ChainSpec(A.DRIFT, T.ADRIFT, WATERBORNE)),
        S.RIGGING: (ChainSpec(A.DRIFT, T.ADRIFT, WATERBORNE),),
        S.SAILS: BURNS,
        S.OARS: NO_CHAIN,
        S.RUDDER: (ChainSpec(A.DRIFT, T.ADRIFT),),
        S.STEERING: (ChainSpec(A.DRIFT, T.ADRIFT),),
        S.ENGINE: DIES_DOWN,
        S.BOILER: EXPLODES,
        S.FUEL_STORE: EXPLODES,
        S.POWER_CORE: EXPLODES,
        S.DRIVE: DIES_DOWN,
        S.WHEELS: NO_CHAIN,
        S.AXLE: NO_CHAIN,
        S.TRACKS: NO_CHAIN,
        S.LEGS: NO_CHAIN,
        S.CHASSIS: NO_CHAIN,
        S.FRAME: NO_CHAIN,
        S.HARNESS: NO_CHAIN,
        S.DRAFT_TEAM: NO_CHAIN,
        S.SADDLE: NO_CHAIN,
        S.MOUNT_BODY: NO_CHAIN,
        S.ARMOUR_PLATING: NO_CHAIN,
        S.BARDING: NO_CHAIN,
        S.TURRET: NO_CHAIN,
        S.GUN_DECK: BURNS,
        S.HARDPOINT: NO_CHAIN,
        S.MAGAZINE: EXPLODES,
        S.WINGS: FALLS,
        S.ENVELOPE: FALLS,
        S.GONDOLA: NO_CHAIN,
        S.ROTOR: FALLS,
        S.TAIL: (ChainSpec(A.DRIFT, T.ADRIFT, LIFTED),),
        S.BALLAST: (ChainSpec(A.FLOOD, T.FLOODING, WATERBORNE),),
        S.LIFE_SUPPORT: VENTS,
        S.AIRLOCK: VENTS,
        S.SENSORS: NO_CHAIN,
        S.NAVIGATION: (ChainSpec(A.DRIFT, T.ADRIFT, DRY),),
        S.WARD: UNWARDED,
        S.ARM: NO_CHAIN,
        S.COUNTERWEIGHT: NO_CHAIN,
        S.RAM_HEAD: NO_CHAIN,
        S.TOWER: NO_CHAIN,
        S.PLATFORM: NO_CHAIN,
        S.CORE: EXPLODES,
    },
)

MOVING_SECTIONS: MappingProxyType[V, frozenset[S]] = total(
    V,
    {
        V.LAND: frozenset({S.WHEELS, S.TRACKS, S.LEGS, S.ENGINE}),
        V.WATER: frozenset({S.SAILS, S.RIGGING, S.MAST, S.OARS, S.RUDDER, S.ENGINE, S.BOILER}),
        V.UNDERWATER: frozenset({S.ENGINE, S.BALLAST, S.RUDDER, S.SENSORS}),
        V.AIR: frozenset({S.WINGS, S.ENVELOPE, S.ROTOR, S.ENGINE, S.TAIL}),
        V.SPACE: frozenset({S.DRIVE, S.SENSORS, S.NAVIGATION, S.POWER_CORE}),
        V.GAS_GIANT: frozenset({S.ENVELOPE, S.ENGINE, S.DRIVE}),
        V.UNDERGROUND: frozenset({S.ENGINE, S.TRACKS, S.NAVIGATION, S.SENSORS}),
        V.PLANAR: frozenset({S.WARD, S.CORE, S.NAVIGATION, S.DRIVE}),
        V.AMPHIBIOUS: frozenset({S.ENGINE, S.WHEELS, S.TRACKS, S.RUDDER}),
    },
)


def chain_of(section: S, domain: V) -> ChainSpec | None:
    return next((spec for spec in SECTION_CHAINS[section] if domain in spec.domains), None)


def reached(damage: D, family: E | None, carried: list[S]) -> list[S]:
    wanted = FAMILY_SECTIONS.get(family, DAMAGE_SECTIONS[damage]) if family is not None else DAMAGE_SECTIONS[damage]
    found = [section for section in wanted if section in carried]
    return found or carried


RAM_ARMS = frozenset({E.RAM, E.HARPOON, E.BOARDING_GEAR})
MISSILE_ARMS = frozenset({E.BALLISTA, E.ROCKET_LAUNCHER, E.MISSILE_LAUNCHER, E.TORPEDO, E.BEAM_CANNON, E.AUTOCANNON, E.MASS_DRIVER, E.PLASMA_CANNON})
ENGINE_ARMS = frozenset({E.CATAPULT_ENGINE, E.TREBUCHET_ENGINE, E.BOMBARD, E.CANNON, E.CARRONADE, E.HOWITZER, E.MORTAR, E.MINE_LAYER, E.HEAVY_FLAMETHROWER})
RITE_ARMS = frozenset({E.FOCUS_ARRAY, E.FOCUS})
WIND_ARMS = frozenset({E.FOCUS_ARRAY, E.FOCUS, E.HEAVY_FLAMETHROWER})
