from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.collective import DesignComponentKind, DesignKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.integrity import Criticality, SectionHazard
from aerona.domain.enums.military import VesselArmament
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.vehicles import (
    MountKind,
    Propulsion,
    VehicleDomain,
    VehicleFamily,
    VehicleFrame,
    VehicleSection,
    VehicleSize,
)

C = DesignComponentKind
R = Criticality
H = SectionHazard
S = VehicleSection
M = MountKind
D = VehicleDomain
Y = VehicleFamily
P = Propulsion
Z = VehicleSize
K = KnowledgeBranch
F = VehicleFrame


@dataclass(frozen=True)
class SectionSpec:
    section: VehicleSection
    function: DesignComponentKind
    criticality: Criticality
    share: int
    exposure: int
    hazard: SectionHazard = SectionHazard.NONE
    neighbours: tuple[VehicleSection, ...] = ()


def part(
    section: VehicleSection,
    function: DesignComponentKind,
    criticality: Criticality,
    weight: tuple[int, int],
    hazard: SectionHazard = SectionHazard.NONE,
    *neighbours: VehicleSection,
) -> SectionSpec:
    return SectionSpec(section, function, criticality, weight[0], weight[1], hazard, neighbours)


LAYOUTS: MappingProxyType[VehicleFamily, tuple[SectionSpec, ...]] = total(
    VehicleFamily,
    {
        Y.MOUNT: (
            part(S.MOUNT_BODY, C.PROPULSION, R.CRITICAL, (60, 60), H.PANIC, S.SADDLE, S.BARDING),
            part(S.SADDLE, C.QUARTERS, R.MINOR, (15, 15), H.NONE, S.MOUNT_BODY),
            part(S.BARDING, C.ARMOUR, R.MINOR, (25, 25), H.NONE, S.MOUNT_BODY),
        ),
        Y.CART: (
            part(S.CHASSIS, C.FRAME, R.CRITICAL, (35, 25), H.NONE, S.WHEELS, S.CARGO_BAY),
            part(S.WHEELS, C.PROPULSION, R.MAJOR, (20, 25), H.NONE, S.CHASSIS),
            part(S.HARNESS, C.STEERING, R.MINOR, (10, 10), H.NONE, S.DRAFT_TEAM),
            part(S.DRAFT_TEAM, C.PROPULSION, R.MAJOR, (15, 20), H.PANIC, S.HARNESS),
            part(S.CARGO_BAY, C.HOLD, R.MINOR, (20, 20), H.FIRE, S.CHASSIS),
        ),
        Y.WAGON: (
            part(S.CHASSIS, C.FRAME, R.CRITICAL, (30, 20), H.NONE, S.WHEELS, S.AXLE, S.CARGO_BAY),
            part(S.WHEELS, C.PROPULSION, R.MAJOR, (15, 20), H.NONE, S.AXLE),
            part(S.AXLE, C.PROPULSION, R.MAJOR, (10, 10), H.NONE, S.WHEELS, S.CHASSIS),
            part(S.HARNESS, C.STEERING, R.MINOR, (5, 5), H.NONE, S.DRAFT_TEAM),
            part(S.DRAFT_TEAM, C.PROPULSION, R.MAJOR, (15, 20), H.PANIC, S.HARNESS),
            part(S.CARGO_BAY, C.HOLD, R.MINOR, (20, 20), H.FIRE, S.CHASSIS),
            part(S.ARMOUR_PLATING, C.ARMOUR, R.MINOR, (5, 5), H.NONE, S.CHASSIS),
        ),
        Y.CHARIOT: (
            part(S.CHASSIS, C.FRAME, R.CRITICAL, (25, 20), H.NONE, S.WHEELS, S.AXLE, S.PLATFORM),
            part(S.WHEELS, C.PROPULSION, R.MAJOR, (15, 20), H.NONE, S.AXLE),
            part(S.AXLE, C.PROPULSION, R.MAJOR, (10, 10), H.NONE, S.WHEELS),
            part(S.DRAFT_TEAM, C.PROPULSION, R.MAJOR, (20, 25), H.PANIC, S.HARNESS),
            part(S.HARNESS, C.STEERING, R.MINOR, (5, 5), H.NONE, S.DRAFT_TEAM),
            part(S.PLATFORM, C.QUARTERS, R.MAJOR, (20, 15), H.NONE, S.CHASSIS),
            part(S.ARMOUR_PLATING, C.ARMOUR, R.MINOR, (5, 5), H.NONE, S.PLATFORM),
        ),
        Y.MOTOR: (
            part(S.CHASSIS, C.FRAME, R.CRITICAL, (30, 20), H.NONE, S.ENGINE, S.WHEELS, S.COCKPIT),
            part(S.ENGINE, C.PROPULSION, R.MAJOR, (15, 15), H.FIRE, S.FUEL_STORE, S.CHASSIS),
            part(S.FUEL_STORE, C.POWER, R.MINOR, (5, 5), H.EXPLOSION, S.ENGINE, S.CARGO_BAY),
            part(S.WHEELS, C.PROPULSION, R.MAJOR, (10, 15), H.NONE, S.CHASSIS),
            part(S.STEERING, C.STEERING, R.MAJOR, (5, 5), H.NONE, S.COCKPIT),
            part(S.COCKPIT, C.COMMAND, R.MAJOR, (10, 10), H.NONE, S.CHASSIS, S.STEERING),
            part(S.CARGO_BAY, C.HOLD, R.MINOR, (15, 15), H.FIRE, S.FUEL_STORE),
            part(S.ARMOUR_PLATING, C.ARMOUR, R.MINOR, (10, 15), H.NONE, S.CHASSIS),
        ),
        Y.TRACKED: (
            part(S.CHASSIS, C.FRAME, R.CRITICAL, (25, 20), H.NONE, S.ENGINE, S.TRACKS, S.TURRET),
            part(S.ENGINE, C.PROPULSION, R.MAJOR, (15, 10), H.FIRE, S.FUEL_STORE, S.CHASSIS),
            part(S.FUEL_STORE, C.POWER, R.MINOR, (5, 5), H.EXPLOSION, S.ENGINE),
            part(S.TRACKS, C.PROPULSION, R.MAJOR, (10, 20), H.NONE, S.CHASSIS),
            part(S.TURRET, C.WEAPON, R.MAJOR, (15, 15), H.NONE, S.MAGAZINE, S.COCKPIT),
            part(S.MAGAZINE, C.WEAPON, R.CRITICAL, (5, 5), H.EXPLOSION, S.TURRET, S.CHASSIS),
            part(S.COCKPIT, C.COMMAND, R.MAJOR, (10, 5), H.NONE, S.TURRET),
            part(S.ARMOUR_PLATING, C.ARMOUR, R.MINOR, (15, 20), H.NONE, S.CHASSIS),
        ),
        Y.WALKER: (
            part(S.FRAME, C.FRAME, R.CRITICAL, (25, 20), H.NONE, S.LEGS, S.POWER_CORE, S.COCKPIT),
            part(S.LEGS, C.PROPULSION, R.MAJOR, (20, 25), H.CRASH, S.FRAME),
            part(S.POWER_CORE, C.POWER, R.CRITICAL, (10, 5), H.EXPLOSION, S.FRAME),
            part(S.COCKPIT, C.COMMAND, R.MAJOR, (10, 10), H.NONE, S.FRAME),
            part(S.HARDPOINT, C.WEAPON, R.MINOR, (15, 15), H.NONE, S.FRAME),
            part(S.ARMOUR_PLATING, C.ARMOUR, R.MINOR, (20, 25), H.NONE, S.FRAME),
        ),
        Y.RAIL: (
            part(S.CHASSIS, C.FRAME, R.CRITICAL, (30, 25), H.NONE, S.WHEELS, S.ENGINE, S.CARGO_BAY),
            part(S.WHEELS, C.PROPULSION, R.MAJOR, (15, 15), H.NONE, S.CHASSIS),
            part(S.ENGINE, C.PROPULSION, R.MAJOR, (15, 15), H.FIRE, S.BOILER),
            part(S.BOILER, C.POWER, R.MAJOR, (10, 10), H.EXPLOSION, S.ENGINE, S.COCKPIT),
            part(S.COCKPIT, C.COMMAND, R.MINOR, (5, 5), H.NONE, S.BOILER),
            part(S.CARGO_BAY, C.HOLD, R.MINOR, (25, 30), H.FIRE, S.CHASSIS),
        ),
        Y.RAM: (
            part(S.FRAME, C.FRAME, R.CRITICAL, (40, 30), H.FIRE, S.RAM_HEAD, S.ARMOUR_PLATING, S.WHEELS),
            part(S.RAM_HEAD, C.WEAPON, R.MAJOR, (25, 30), H.NONE, S.FRAME),
            part(S.WHEELS, C.PROPULSION, R.MINOR, (10, 10), H.NONE, S.FRAME),
            part(S.ARMOUR_PLATING, C.ARMOUR, R.MINOR, (25, 30), H.FIRE, S.FRAME),
        ),
        Y.TOWER: (
            part(S.FRAME, C.FRAME, R.CRITICAL, (35, 30), H.FIRE, S.TOWER, S.WHEELS, S.ARMOUR_PLATING),
            part(S.TOWER, C.TROOPS, R.MAJOR, (25, 25), H.FIRE, S.FRAME, S.PLATFORM),
            part(S.PLATFORM, C.WEAPON, R.MINOR, (10, 10), H.NONE, S.TOWER),
            part(S.WHEELS, C.PROPULSION, R.MAJOR, (10, 10), H.NONE, S.FRAME),
            part(S.ARMOUR_PLATING, C.ARMOUR, R.MINOR, (20, 25), H.FIRE, S.FRAME, S.TOWER),
        ),
        Y.THROWER: (
            part(S.FRAME, C.FRAME, R.CRITICAL, (35, 35), H.FIRE, S.ARM, S.COUNTERWEIGHT, S.WHEELS),
            part(S.ARM, C.WEAPON, R.MAJOR, (25, 25), H.NONE, S.FRAME),
            part(S.COUNTERWEIGHT, C.COUNTERWEIGHT, R.MAJOR, (20, 15), H.NONE, S.FRAME),
            part(S.WHEELS, C.PROPULSION, R.MINOR, (10, 15), H.NONE, S.FRAME),
            part(S.CREW_QUARTERS, C.QUARTERS, R.MINOR, (10, 10), H.NONE, S.FRAME),
        ),
        Y.GUN: (
            part(S.CHASSIS, C.FRAME, R.CRITICAL, (35, 35), H.NONE, S.HARDPOINT, S.WHEELS),
            part(S.HARDPOINT, C.WEAPON, R.MAJOR, (30, 25), H.NONE, S.CHASSIS, S.MAGAZINE),
            part(S.MAGAZINE, C.WEAPON, R.MAJOR, (10, 10), H.EXPLOSION, S.HARDPOINT),
            part(S.WHEELS, C.PROPULSION, R.MINOR, (15, 20), H.NONE, S.CHASSIS),
            part(S.CREW_QUARTERS, C.QUARTERS, R.MINOR, (10, 10), H.NONE, S.CHASSIS),
        ),
        Y.BOAT: (
            part(S.HULL, C.HULL, R.CRITICAL, (50, 45), H.FLOODING, S.OARS, S.HOLD, S.RUDDER),
            part(S.OARS, C.PROPULSION, R.MAJOR, (20, 25), H.NONE, S.HULL),
            part(S.RUDDER, C.STEERING, R.MINOR, (10, 10), H.NONE, S.HULL),
            part(S.HOLD, C.HOLD, R.MINOR, (20, 20), H.NONE, S.HULL),
        ),
        Y.GALLEY: (
            part(S.HULL, C.HULL, R.CRITICAL, (25, 25), H.FLOODING, S.KEEL, S.OARS, S.HOLD),
            part(S.KEEL, C.FRAME, R.CRITICAL, (10, 5), H.NONE, S.HULL),
            part(S.DECK, C.QUARTERS, R.MAJOR, (15, 15), H.FIRE, S.OARS, S.MAST),
            part(S.OARS, C.PROPULSION, R.MAJOR, (15, 20), H.NONE, S.HULL, S.DECK),
            part(S.MAST, C.PROPULSION, R.MINOR, (5, 5), H.NONE, S.SAILS, S.DECK),
            part(S.SAILS, C.PROPULSION, R.MINOR, (5, 5), H.FIRE, S.MAST),
            part(S.RUDDER, C.STEERING, R.MAJOR, (5, 5), H.NONE, S.STERN),
            part(S.STERN, C.COMMAND, R.MINOR, (5, 5), H.NONE, S.RUDDER, S.DECK),
            part(S.BOW, C.WEAPON, R.MINOR, (5, 5), H.NONE, S.HULL),
            part(S.HOLD, C.HOLD, R.MINOR, (10, 10), H.FIRE, S.HULL),
        ),
        Y.SAILING_SHIP: (
            part(S.HULL, C.HULL, R.CRITICAL, (25, 25), H.FLOODING, S.KEEL, S.HOLD, S.GUN_DECK),
            part(S.KEEL, C.FRAME, R.CRITICAL, (8, 3), H.NONE, S.HULL),
            part(S.DECK, C.QUARTERS, R.MAJOR, (10, 10), H.FIRE, S.MAST, S.GUN_DECK),
            part(S.MAST, C.PROPULSION, R.MAJOR, (8, 8), H.NONE, S.RIGGING, S.DECK),
            part(S.RIGGING, C.PROPULSION, R.MINOR, (5, 8), H.FIRE, S.MAST, S.SAILS),
            part(S.SAILS, C.PROPULSION, R.MINOR, (6, 10), H.FIRE, S.RIGGING),
            part(S.RUDDER, C.STEERING, R.MAJOR, (4, 4), H.NONE, S.STERN),
            part(S.STERN, C.COMMAND, R.MINOR, (4, 4), H.NONE, S.RUDDER, S.DECK),
            part(S.GUN_DECK, C.WEAPON, R.MAJOR, (12, 12), H.FIRE, S.MAGAZINE, S.HULL),
            part(S.MAGAZINE, C.WEAPON, R.CRITICAL, (3, 3), H.EXPLOSION, S.GUN_DECK, S.HOLD),
            part(S.HOLD, C.HOLD, R.MINOR, (10, 8), H.FIRE, S.HULL, S.MAGAZINE),
            part(S.CREW_QUARTERS, C.QUARTERS, R.MINOR, (3, 3), H.NONE, S.DECK),
            part(S.NAVIGATION, C.NAVIGATION, R.MINOR, (2, 2), H.NONE, S.STERN),
        ),
        Y.STEAM_SHIP: (
            part(S.HULL, C.HULL, R.CRITICAL, (22, 22), H.FLOODING, S.KEEL, S.ENGINE, S.HOLD),
            part(S.KEEL, C.FRAME, R.CRITICAL, (8, 3), H.NONE, S.HULL),
            part(S.ENGINE, C.PROPULSION, R.MAJOR, (10, 8), H.FIRE, S.BOILER, S.FUEL_STORE),
            part(S.BOILER, C.POWER, R.CRITICAL, (6, 5), H.EXPLOSION, S.ENGINE, S.HULL),
            part(S.FUEL_STORE, C.POWER, R.MINOR, (5, 5), H.FIRE, S.ENGINE, S.HOLD),
            part(S.RUDDER, C.STEERING, R.MAJOR, (4, 4), H.NONE, S.HULL),
            part(S.BRIDGE, C.COMMAND, R.MAJOR, (5, 6), H.NONE, S.DECK),
            part(S.DECK, C.QUARTERS, R.MINOR, (8, 10), H.FIRE, S.BRIDGE, S.TURRET),
            part(S.TURRET, C.WEAPON, R.MAJOR, (10, 12), H.NONE, S.MAGAZINE, S.DECK),
            part(S.MAGAZINE, C.WEAPON, R.CRITICAL, (3, 3), H.EXPLOSION, S.TURRET, S.HULL),
            part(S.ARMOUR_PLATING, C.ARMOUR, R.MINOR, (10, 15), H.NONE, S.HULL),
            part(S.HOLD, C.HOLD, R.MINOR, (6, 5), H.FIRE, S.FUEL_STORE),
            part(S.CREW_QUARTERS, C.QUARTERS, R.MINOR, (3, 2), H.NONE, S.DECK),
        ),
        Y.SUBMARINE: (
            part(S.HULL, C.HULL, R.CRITICAL, (30, 30), H.BREACH, S.BALLAST, S.LIFE_SUPPORT, S.ENGINE),
            part(S.BALLAST, C.LIFT, R.MAJOR, (10, 10), H.FLOODING, S.HULL),
            part(S.ENGINE, C.PROPULSION, R.MAJOR, (12, 10), H.FIRE, S.POWER_CORE),
            part(S.POWER_CORE, C.POWER, R.MAJOR, (10, 8), H.EXPLOSION, S.ENGINE, S.HULL),
            part(S.LIFE_SUPPORT, C.LIFE_SUPPORT, R.CRITICAL, (8, 7), H.BREACH, S.HULL, S.BRIDGE),
            part(S.BRIDGE, C.COMMAND, R.MAJOR, (8, 8), H.NONE, S.LIFE_SUPPORT),
            part(S.HARDPOINT, C.WEAPON, R.MAJOR, (12, 15), H.NONE, S.MAGAZINE),
            part(S.MAGAZINE, C.WEAPON, R.CRITICAL, (5, 5), H.EXPLOSION, S.HARDPOINT, S.HULL),
            part(S.SENSORS, C.NAVIGATION, R.MINOR, (5, 7), H.NONE, S.BRIDGE),
        ),
        Y.BALLOON: (
            part(S.ENVELOPE, C.LIFT, R.CRITICAL, (55, 60), H.CRASH, S.GONDOLA),
            part(S.GONDOLA, C.QUARTERS, R.MAJOR, (30, 25), H.NONE, S.ENVELOPE, S.BALLAST),
            part(S.BALLAST, C.LIFT, R.MINOR, (15, 15), H.NONE, S.GONDOLA),
        ),
        Y.AIRSHIP: (
            part(S.ENVELOPE, C.LIFT, R.CRITICAL, (35, 40), H.CRASH, S.GONDOLA, S.ENGINE),
            part(S.FRAME, C.FRAME, R.CRITICAL, (10, 5), H.NONE, S.ENVELOPE),
            part(S.GONDOLA, C.COMMAND, R.MAJOR, (12, 10), H.NONE, S.ENVELOPE, S.CARGO_BAY),
            part(S.ENGINE, C.PROPULSION, R.MAJOR, (10, 10), H.FIRE, S.FUEL_STORE, S.ENVELOPE),
            part(S.FUEL_STORE, C.POWER, R.MINOR, (5, 5), H.EXPLOSION, S.ENGINE),
            part(S.RUDDER, C.STEERING, R.MINOR, (5, 5), H.NONE, S.FRAME),
            part(S.CARGO_BAY, C.HOLD, R.MINOR, (13, 15), H.FIRE, S.GONDOLA),
            part(S.HARDPOINT, C.WEAPON, R.MINOR, (10, 10), H.NONE, S.GONDOLA),
        ),
        Y.AIRCRAFT: (
            part(S.FRAME, C.FRAME, R.CRITICAL, (25, 25), H.NONE, S.WINGS, S.ENGINE, S.COCKPIT, S.TAIL),
            part(S.WINGS, C.LIFT, R.CRITICAL, (20, 25), H.CRASH, S.FRAME, S.FUEL_STORE),
            part(S.ENGINE, C.PROPULSION, R.MAJOR, (15, 12), H.FIRE, S.FUEL_STORE, S.FRAME),
            part(S.FUEL_STORE, C.POWER, R.MINOR, (8, 8), H.EXPLOSION, S.WINGS, S.ENGINE),
            part(S.TAIL, C.STEERING, R.MAJOR, (10, 10), H.CRASH, S.FRAME),
            part(S.COCKPIT, C.COMMAND, R.CRITICAL, (10, 8), H.NONE, S.FRAME),
            part(S.HARDPOINT, C.WEAPON, R.MINOR, (12, 12), H.NONE, S.WINGS),
        ),
        Y.ROTORCRAFT: (
            part(S.FRAME, C.FRAME, R.CRITICAL, (25, 25), H.NONE, S.ROTOR, S.ENGINE, S.COCKPIT, S.TAIL),
            part(S.ROTOR, C.LIFT, R.CRITICAL, (15, 15), H.CRASH, S.ENGINE),
            part(S.ENGINE, C.PROPULSION, R.MAJOR, (15, 12), H.FIRE, S.FUEL_STORE, S.ROTOR),
            part(S.FUEL_STORE, C.POWER, R.MINOR, (5, 8), H.EXPLOSION, S.ENGINE),
            part(S.TAIL, C.STEERING, R.MAJOR, (10, 12), H.CRASH, S.FRAME),
            part(S.COCKPIT, C.COMMAND, R.CRITICAL, (10, 8), H.NONE, S.FRAME),
            part(S.TROOP_BAY, C.TROOPS, R.MINOR, (12, 12), H.NONE, S.FRAME),
            part(S.HARDPOINT, C.WEAPON, R.MINOR, (8, 8), H.NONE, S.FRAME),
        ),
        Y.SPACECRAFT: (
            part(S.HULL, C.HULL, R.CRITICAL, (20, 22), H.BREACH, S.DRIVE, S.LIFE_SUPPORT, S.CARGO_BAY, S.CREW_QUARTERS),
            part(S.DRIVE, C.PROPULSION, R.MAJOR, (10, 8), H.FIRE, S.POWER_CORE, S.HULL),
            part(S.POWER_CORE, C.POWER, R.CRITICAL, (8, 5), H.EXPLOSION, S.DRIVE, S.HULL),
            part(S.LIFE_SUPPORT, C.LIFE_SUPPORT, R.CRITICAL, (6, 5), H.BREACH, S.HULL, S.CREW_QUARTERS),
            part(S.BRIDGE, C.COMMAND, R.MAJOR, (6, 6), H.BREACH, S.SENSORS, S.HULL),
            part(S.CREW_QUARTERS, C.QUARTERS, R.MINOR, (6, 6), H.BREACH, S.LIFE_SUPPORT),
            part(S.CARGO_BAY, C.HOLD, R.MINOR, (8, 8), H.NONE, S.HULL, S.AIRLOCK),
            part(S.SENSORS, C.NAVIGATION, R.MINOR, (4, 6), H.NONE, S.BRIDGE),
            part(S.TURRET, C.WEAPON, R.MAJOR, (8, 10), H.NONE, S.MAGAZINE, S.HULL),
            part(S.MAGAZINE, C.WEAPON, R.CRITICAL, (3, 3), H.EXPLOSION, S.TURRET, S.HULL),
            part(S.WARD, C.WARD, R.MINOR, (5, 5), H.NONE, S.HULL),
            part(S.AIRLOCK, C.QUARTERS, R.MINOR, (3, 4), H.BREACH, S.CARGO_BAY),
            part(S.ARMOUR_PLATING, C.ARMOUR, R.MINOR, (13, 12), H.NONE, S.HULL),
        ),
        Y.BURROWER: (
            part(S.HULL, C.HULL, R.CRITICAL, (30, 25), H.BREACH, S.RAM_HEAD, S.ENGINE, S.LIFE_SUPPORT),
            part(S.RAM_HEAD, C.PROPULSION, R.MAJOR, (20, 30), H.NONE, S.HULL),
            part(S.ENGINE, C.POWER, R.MAJOR, (15, 12), H.FIRE, S.HULL),
            part(S.LIFE_SUPPORT, C.LIFE_SUPPORT, R.CRITICAL, (10, 8), H.BREACH, S.COCKPIT),
            part(S.COCKPIT, C.COMMAND, R.MAJOR, (10, 10), H.NONE, S.LIFE_SUPPORT),
            part(S.CARGO_BAY, C.HOLD, R.MINOR, (15, 15), H.NONE, S.HULL),
        ),
        Y.CONSTRUCT: (
            part(S.CORE, C.POWER, R.CRITICAL, (15, 10), H.EXPLOSION, S.FRAME),
            part(S.FRAME, C.FRAME, R.CRITICAL, (25, 25), H.NONE, S.CORE, S.LEGS, S.ARM),
            part(S.LEGS, C.PROPULSION, R.MAJOR, (15, 20), H.CRASH, S.FRAME),
            part(S.ARM, C.WEAPON, R.MAJOR, (15, 20), H.NONE, S.FRAME),
            part(S.WARD, C.WARD, R.MINOR, (10, 5), H.NONE, S.CORE),
            part(S.PLATFORM, C.TROOPS, R.MINOR, (5, 5), H.NONE, S.FRAME),
            part(S.ARMOUR_PLATING, C.ARMOUR, R.MINOR, (15, 15), H.NONE, S.FRAME),
        ),
        Y.LIVING: (
            part(S.CORE, C.LIFE_SUPPORT, R.CRITICAL, (15, 8), H.NONE, S.HULL),
            part(S.HULL, C.HULL, R.CRITICAL, (30, 30), H.FLOODING, S.CORE, S.DRIVE, S.HOLD),
            part(S.DRIVE, C.PROPULSION, R.MAJOR, (15, 20), H.NONE, S.HULL),
            part(S.SENSORS, C.NAVIGATION, R.MINOR, (8, 8), H.NONE, S.CORE),
            part(S.CREW_QUARTERS, C.QUARTERS, R.MINOR, (10, 10), H.NONE, S.HULL),
            part(S.HOLD, C.HOLD, R.MINOR, (12, 14), H.NONE, S.HULL),
            part(S.WARD, C.WARD, R.MINOR, (10, 10), H.NONE, S.CORE),
        ),
    },
)

MOUNTS: MappingProxyType[VehicleFamily, tuple[MountKind, ...]] = total(
    VehicleFamily,
    {
        Y.MOUNT: (M.RIDER,),
        Y.CART: (),
        Y.WAGON: (M.CREW_STATION,),
        Y.CHARIOT: (M.RIDER, M.CREW_STATION),
        Y.MOTOR: (M.HARDPOINT,),
        Y.TRACKED: (M.TURRET, M.HARDPOINT),
        Y.WALKER: (M.HARDPOINT, M.HARDPOINT),
        Y.RAIL: (M.HARDPOINT,),
        Y.RAM: (M.RAM,),
        Y.TOWER: (M.DECK, M.CREW_STATION),
        Y.THROWER: (M.DECK,),
        Y.GUN: (M.DECK,),
        Y.BOAT: (M.CREW_STATION,),
        Y.GALLEY: (M.RAM, M.BOW, M.DECK),
        Y.SAILING_SHIP: (M.BROADSIDE, M.BROADSIDE, M.BOW, M.STERN, M.DECK),
        Y.STEAM_SHIP: (M.TURRET, M.TURRET, M.BROADSIDE, M.DECK),
        Y.SUBMARINE: (M.BAY, M.DECK),
        Y.BALLOON: (M.CREW_STATION,),
        Y.AIRSHIP: (M.HARDPOINT, M.BAY),
        Y.AIRCRAFT: (M.WING, M.WING, M.BAY),
        Y.ROTORCRAFT: (M.HARDPOINT, M.CREW_STATION),
        Y.SPACECRAFT: (M.TURRET, M.TURRET, M.SPINAL, M.BAY, M.WARD_NODE),
        Y.BURROWER: (M.RAM,),
        Y.CONSTRUCT: (M.HARDPOINT, M.WARD_NODE),
        Y.LIVING: (M.BOW, M.WARD_NODE),
    },
)


@dataclass(frozen=True)
class FrameSpec:
    frame: VehicleFrame
    label: str
    domain: VehicleDomain
    family: VehicleFamily
    propulsion: Propulsion
    size: VehicleSize
    speed: int
    range: int
    cargo: int
    crew: int
    troops: int
    endurance: int
    armour: int
    structure: int
    branch: KnowledgeBranch | None = None
    level: int = 0
    strangeness: int = 0
    armament: tuple[VesselArmament, ...] = ()

    @property
    def kind(self) -> DesignKind:
        return DESIGN_KINDS[self.domain] if self.family not in SIEGE_FAMILIES else DesignKind.SIEGE_ENGINE

    @property
    def sky(self) -> bool:
        return self.domain is VehicleDomain.AIR

    @property
    def living(self) -> bool:
        return self.family is VehicleFamily.LIVING

    @property
    def slots(self) -> int:
        return len(MOUNTS[self.family])


SIEGE_FAMILIES = frozenset({Y.RAM, Y.TOWER, Y.THROWER, Y.GUN})
DESIGN_KINDS: MappingProxyType[VehicleDomain, DesignKind] = total(
    VehicleDomain,
    {
        D.LAND: DesignKind.LAND_VEHICLE,
        D.WATER: DesignKind.VESSEL,
        D.UNDERWATER: DesignKind.VESSEL,
        D.AIR: DesignKind.SKYSHIP,
        D.SPACE: DesignKind.SPACECRAFT,
        D.GAS_GIANT: DesignKind.SPACECRAFT,
        D.UNDERGROUND: DesignKind.LAND_VEHICLE,
        D.PLANAR: DesignKind.SPACECRAFT,
        D.AMPHIBIOUS: DesignKind.VESSEL,
    },
)
FUELS: MappingProxyType[Propulsion, CommodityKind | None] = total(
    Propulsion,
    {
        P.CREW: None,
        P.DRAFT_ANIMALS: CommodityKind.FODDER,
        P.RIDDEN: CommodityKind.FODDER,
        P.OARS: None,
        P.SAIL: None,
        P.SAIL_AND_OAR: None,
        P.STEAM: CommodityKind.COAL,
        P.COMBUSTION: CommodityKind.FUEL,
        P.ELECTRIC: CommodityKind.FUEL,
        P.REACTION: CommodityKind.FUEL,
        P.SOLAR_SAIL: None,
        P.FOLD_DRIVE: CommodityKind.MAGICAL_REAGENTS,
        P.BUOYANCY: None,
        P.MAGIC: CommodityKind.MAGICAL_REAGENTS,
        P.DIVINE: None,
        P.SELF: CommodityKind.FODDER,
        P.CURRENT: None,
        P.TOWED: None,
    },
)
V = VesselArmament


def frame(
    head: tuple[VehicleFrame, str, VehicleDomain, VehicleFamily, Propulsion, VehicleSize],
    values: tuple[int, int, int, int, int, int, int, int],
    gate: tuple[KnowledgeBranch | None, int] = (None, 0),
    strangeness: int = 0,
    armament: tuple[VesselArmament, ...] = (),
) -> FrameSpec:
    name, label, domain, family, propulsion, size = head
    speed, reach, cargo, crew, troops, endurance, armour, structure = values
    branch, level = gate
    return FrameSpec(
        name,
        label,
        domain,
        family,
        propulsion,
        size,
        speed,
        reach,
        cargo,
        crew,
        troops,
        endurance,
        armour,
        structure,
        branch,
        level,
        strangeness,
        armament,
    )


FRAMES: MappingProxyType[VehicleFrame, FrameSpec] = total(
    VehicleFrame,
    {
        spec.frame: spec
        for spec in (
            frame((F.RIDING_MOUNT, "Riding mount", D.LAND, Y.MOUNT, P.RIDDEN, Z.SMALL), (60, 40, 5, 1, 0, 40, 5, 20)),
            frame((F.PACK_MOUNT, "Pack mount", D.LAND, Y.MOUNT, P.RIDDEN, Z.SMALL), (35, 40, 20, 1, 0, 45, 0, 20)),
            frame((F.TRAVOIS, "Travois", D.LAND, Y.CART, P.DRAFT_ANIMALS, Z.SMALL), (25, 25, 25, 1, 0, 30, 0, 10)),
            frame((F.SLEDGE, "Sledge", D.LAND, Y.CART, P.DRAFT_ANIMALS, Z.SMALL), (35, 35, 40, 1, 0, 50, 0, 15)),
            frame((F.HANDCART, "Handcart", D.LAND, Y.CART, P.CREW, Z.SMALL), (15, 15, 20, 1, 0, 25, 0, 10)),
            frame((F.CART, "Cart", D.LAND, Y.CART, P.DRAFT_ANIMALS, Z.SMALL), (25, 30, 60, 1, 0, 30, 0, 20), (K.AGRICULTURE, 1)),
            frame((F.WAGON, "Wagon", D.LAND, Y.WAGON, P.DRAFT_ANIMALS, Z.MEDIUM), (25, 35, 120, 2, 4, 35, 5, 30), (K.TRADE, 1)),
            frame((F.COVERED_WAGON, "Covered wagon", D.LAND, Y.WAGON, P.DRAFT_ANIMALS, Z.MEDIUM), (22, 45, 140, 2, 6, 50, 5, 30), (K.TRADE, 2)),
            frame((F.CARRIAGE, "Carriage", D.LAND, Y.WAGON, P.DRAFT_ANIMALS, Z.MEDIUM), (40, 40, 30, 2, 6, 40, 5, 25), (K.TRADE, 2)),
            frame(
                (F.CHARIOT, "Chariot", D.LAND, Y.CHARIOT, P.DRAFT_ANIMALS, Z.SMALL),
                (65, 30, 5, 2, 0, 30, 15, 25),
                (K.WARFARE, 1),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.WAR_WAGON, "War wagon", D.LAND, Y.WAGON, P.DRAFT_ANIMALS, Z.MEDIUM),
                (20, 30, 40, 4, 8, 40, 35, 45),
                (K.WARFARE, 2),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.BEAST_CARRIER, "Beast carrier", D.LAND, Y.MOUNT, P.RIDDEN, Z.LARGE),
                (30, 35, 60, 3, 8, 45, 30, 70),
                (K.WARFARE, 2),
                armament=(V.MISSILES,),
            ),
            frame((F.RAIL_CAR, "Rail car", D.LAND, Y.RAIL, P.TOWED, Z.LARGE), (50, 60, 300, 2, 40, 60, 10, 50), (K.METALLURGY, 4)),
            frame((F.LOCOMOTIVE, "Locomotive", D.LAND, Y.RAIL, P.STEAM, Z.LARGE), (60, 60, 50, 4, 0, 65, 20, 70), (K.METALLURGY, 4)),
            frame((F.STEAM_CARRIAGE, "Steam carriage", D.LAND, Y.MOTOR, P.STEAM, Z.MEDIUM), (45, 50, 60, 2, 4, 45, 10, 35), (K.METALLURGY, 4)),
            frame((F.MOTOR_CAR, "Motor car", D.LAND, Y.MOTOR, P.COMBUSTION, Z.SMALL), (75, 70, 30, 1, 3, 50, 5, 30), (K.METALLURGY, 5)),
            frame((F.MOTOR_TRUCK, "Motor truck", D.LAND, Y.MOTOR, P.COMBUSTION, Z.MEDIUM), (60, 75, 200, 2, 16, 55, 10, 45), (K.METALLURGY, 5)),
            frame((F.MOTORCYCLE, "Motorcycle", D.LAND, Y.MOTOR, P.COMBUSTION, Z.SMALL), (85, 60, 5, 1, 1, 40, 0, 15), (K.METALLURGY, 5)),
            frame(
                (F.ARMOURED_CAR, "Armoured car", D.LAND, Y.MOTOR, P.COMBUSTION, Z.MEDIUM),
                (65, 65, 20, 3, 4, 55, 45, 60),
                (K.WARFARE, 5),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.TANK, "Tank", D.LAND, Y.TRACKED, P.COMBUSTION, Z.LARGE),
                (40, 55, 10, 4, 0, 65, 80, 90),
                (K.WARFARE, 5),
                armament=(V.SIEGE_ENGINES, V.MISSILES),
            ),
            frame(
                (F.WALKER, "Walker", D.LAND, Y.WALKER, P.ELECTRIC, Z.LARGE),
                (45, 55, 20, 2, 0, 60, 60, 80),
                (K.METALLURGY, 6),
                armament=(V.SIEGE_ENGINES, V.MISSILES),
            ),
            frame((F.CRAWLER, "Crawler", D.LAND, Y.TRACKED, P.COMBUSTION, Z.HUGE), (20, 60, 500, 8, 30, 75, 50, 120), (K.METALLURGY, 5)),
            frame(
                (F.CONSTRUCT_WALKER, "Construct walker", D.LAND, Y.CONSTRUCT, P.MAGIC, Z.LARGE),
                (35, 40, 20, 1, 0, 70, 55, 90),
                (K.MAGIC, 3),
                20,
                (V.RAMS, V.RITES),
            ),
            frame((F.CONSTRUCT_CARRIER, "Construct carrier", D.LAND, Y.CONSTRUCT, P.MAGIC, Z.HUGE), (25, 45, 200, 2, 20, 75, 45, 110), (K.MAGIC, 4), 25),
            frame(
                (F.BATTERING_RAM, "Battering ram", D.LAND, Y.RAM, P.CREW, Z.MEDIUM),
                (10, 5, 0, 12, 0, 40, 30, 45),
                (K.WARFARE, 1),
                armament=(V.RAMS,),
            ),
            frame(
                (F.SIEGE_TOWER, "Siege tower", D.LAND, Y.TOWER, P.CREW, Z.LARGE),
                (5, 5, 0, 10, 40, 35, 35, 60),
                (K.WARFARE, 2),
                armament=(V.MISSILES,),
            ),
            frame((F.MANTLET, "Mantlet", D.LAND, Y.RAM, P.CREW, Z.SMALL), (10, 5, 0, 4, 6, 40, 40, 25), (K.WARFARE, 1)),
            frame(
                (F.CATAPULT, "Catapult", D.LAND, Y.THROWER, P.TOWED, Z.MEDIUM),
                (10, 10, 0, 8, 0, 35, 10, 35),
                (K.WARFARE, 2),
                armament=(V.SIEGE_ENGINES,),
            ),
            frame(
                (F.TREBUCHET, "Trebuchet", D.LAND, Y.THROWER, P.TOWED, Z.LARGE),
                (5, 5, 0, 15, 0, 40, 10, 50),
                (K.WARFARE, 3),
                armament=(V.SIEGE_ENGINES,),
            ),
            frame(
                (F.BALLISTA, "Ballista", D.LAND, Y.THROWER, P.TOWED, Z.SMALL),
                (15, 10, 0, 4, 0, 35, 10, 25),
                (K.WARFARE, 2),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.BOMBARD, "Bombard", D.LAND, Y.GUN, P.TOWED, Z.LARGE),
                (5, 10, 0, 10, 0, 40, 15, 55),
                (K.METALLURGY, 3),
                armament=(V.SIEGE_ENGINES,),
            ),
            frame(
                (F.FIELD_GUN, "Field gun", D.LAND, Y.GUN, P.TOWED, Z.MEDIUM),
                (20, 20, 0, 6, 0, 45, 15, 40),
                (K.METALLURGY, 4),
                armament=(V.SIEGE_ENGINES,),
            ),
            frame(
                (F.MORTAR, "Mortar", D.LAND, Y.GUN, P.TOWED, Z.SMALL),
                (15, 15, 0, 4, 0, 45, 15, 30),
                (K.METALLURGY, 4),
                armament=(V.SIEGE_ENGINES,),
            ),
            frame(
                (F.ROCKET_BATTERY, "Rocket battery", D.LAND, Y.GUN, P.TOWED, Z.MEDIUM),
                (25, 30, 0, 5, 0, 45, 10, 35),
                (K.METALLURGY, 5),
                armament=(V.SIEGE_ENGINES, V.MISSILES),
            ),
            frame((F.RAFT, "Raft", D.WATER, Y.BOAT, P.CURRENT, Z.SMALL), (15, 10, 20, 4, 4, 10, 0, 10)),
            frame((F.CANOE, "Canoe", D.WATER, Y.BOAT, P.CREW, Z.SMALL), (35, 20, 10, 2, 2, 20, 0, 10)),
            frame((F.ROWBOAT, "Rowboat", D.WATER, Y.BOAT, P.OARS, Z.SMALL), (25, 15, 20, 4, 4, 20, 0, 15)),
            frame((F.BOAT, "Boat", D.WATER, Y.BOAT, P.OARS, Z.SMALL), (30, 20, 40, 8, 6, 25, 0, 20)),
            frame((F.RIVER_BARGE, "River barge", D.WATER, Y.BOAT, P.TOWED, Z.MEDIUM), (15, 30, 250, 6, 20, 20, 0, 35), (K.TRADE, 1)),
            frame((F.SAILBOAT, "Sailboat", D.WATER, Y.BOAT, P.SAIL, Z.SMALL), (40, 30, 40, 4, 4, 30, 0, 20), (K.SEAFARING, 1)),
            frame(
                (F.GALLEY, "Galley", D.WATER, Y.GALLEY, P.SAIL_AND_OAR, Z.MEDIUM),
                (55, 35, 80, 120, 40, 35, 10, 50),
                (K.SEAFARING, 1),
                armament=(V.RAMS, V.MISSILES),
            ),
            frame(
                (F.LONGSHIP, "Longship", D.WATER, Y.GALLEY, P.SAIL_AND_OAR, Z.MEDIUM),
                (65, 55, 60, 50, 30, 45, 5, 45),
                (K.SEAFARING, 1),
                armament=(V.RAMS,),
            ),
            frame(
                (F.COG, "Cog", D.WATER, Y.SAILING_SHIP, P.SAIL, Z.MEDIUM),
                (40, 60, 200, 25, 30, 55, 10, 55),
                (K.SHIPBUILDING, 1),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.CARRACK, "Carrack", D.WATER, Y.SAILING_SHIP, P.SAIL, Z.LARGE),
                (50, 85, 320, 60, 60, 70, 15, 70),
                (K.SHIPBUILDING, 2),
                armament=(V.MISSILES, V.SIEGE_ENGINES),
            ),
            frame(
                (F.GALLEON, "Galleon", D.WATER, Y.SAILING_SHIP, P.SAIL, Z.LARGE),
                (50, 90, 400, 120, 80, 72, 20, 80),
                (K.SHIPBUILDING, 3),
                armament=(V.MISSILES, V.SIEGE_ENGINES),
            ),
            frame(
                (F.FRIGATE, "Frigate", D.WATER, Y.SAILING_SHIP, P.SAIL, Z.LARGE),
                (65, 85, 150, 150, 40, 70, 20, 70),
                (K.SHIPBUILDING, 3),
                armament=(V.SIEGE_ENGINES, V.MISSILES),
            ),
            frame(
                (F.WARSHIP, "Warship", D.WATER, Y.SAILING_SHIP, P.SAIL, Z.LARGE),
                (50, 70, 120, 200, 80, 65, 25, 80),
                (K.SHIPBUILDING, 2),
                armament=(V.RAMS, V.MISSILES, V.SIEGE_ENGINES),
            ),
            frame(
                (F.SHIP_OF_THE_LINE, "Ship of the line", D.WATER, Y.SAILING_SHIP, P.SAIL, Z.HUGE),
                (40, 75, 200, 600, 100, 75, 35, 110),
                (K.SHIPBUILDING, 4),
                armament=(V.SIEGE_ENGINES, V.MISSILES),
            ),
            frame((F.STEAMSHIP, "Steamship", D.WATER, Y.STEAM_SHIP, P.STEAM, Z.LARGE), (60, 100, 500, 80, 100, 80, 15, 90), (K.SHIPBUILDING, 4)),
            frame(
                (F.IRONCLAD, "Ironclad", D.WATER, Y.STEAM_SHIP, P.STEAM, Z.LARGE),
                (45, 80, 150, 200, 60, 75, 70, 110),
                (K.SHIPBUILDING, 4),
                armament=(V.SIEGE_ENGINES, V.RAMS),
            ),
            frame(
                (F.BATTLESHIP, "Battleship", D.WATER, Y.STEAM_SHIP, P.COMBUSTION, Z.HUGE),
                (55, 110, 200, 1200, 200, 85, 90, 160),
                (K.SHIPBUILDING, 5),
                armament=(V.SIEGE_ENGINES, V.MISSILES),
            ),
            frame(
                (F.SUBMARINE, "Submarine", D.UNDERWATER, Y.SUBMARINE, P.ELECTRIC, Z.LARGE),
                (45, 100, 50, 50, 10, 80, 30, 70),
                (K.SHIPBUILDING, 5),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.LIVING_SHIP, "Living ship", D.WATER, Y.LIVING, P.SELF, Z.LARGE),
                (70, 90, 150, 30, 40, 75, 25, 80),
                (K.MAGIC, 3),
                55,
                (V.RAMS, V.RITES),
            ),
            frame(
                (F.FIRE_SHIP, "Fire ship", D.WATER, Y.BOAT, P.SAIL, Z.MEDIUM),
                (45, 20, 0, 6, 0, 30, 0, 25),
                (K.SEAFARING, 2),
                armament=(V.SIEGE_ENGINES,),
            ),
            frame((F.BALLOON, "Balloon", D.AIR, Y.BALLOON, P.BUOYANCY, Z.SMALL), (20, 30, 15, 2, 2, 20, 0, 10), (K.SKY_NAVIGATION, 1)),
            frame(
                (F.AIRSHIP, "Airship", D.AIR, Y.AIRSHIP, P.COMBUSTION, Z.HUGE),
                (55, 100, 150, 30, 40, 45, 10, 70),
                (K.SKY_NAVIGATION, 3),
                armament=(V.MISSILES,),
            ),
            frame((F.GLIDER, "Glider", D.AIR, Y.AIRCRAFT, P.BUOYANCY, Z.SMALL), (50, 25, 5, 1, 1, 20, 0, 10), (K.SKY_NAVIGATION, 1)),
            frame((F.ORNITHOPTER, "Ornithopter", D.AIR, Y.AIRCRAFT, P.CREW, Z.SMALL), (55, 30, 5, 1, 1, 25, 0, 15), (K.SKY_NAVIGATION, 2), 10),
            frame(
                (F.SKY_SAILER, "Sky sailer", D.AIR, Y.AIRSHIP, P.SAIL, Z.LARGE),
                (75, 80, 100, 30, 30, 40, 10, 55),
                (K.SKY_NAVIGATION, 1),
                20,
                (V.MISSILES, V.RITES),
            ),
            frame(
                (F.SKYSHIP, "Skyship", D.AIR, Y.AIRSHIP, P.MAGIC, Z.LARGE),
                (85, 80, 100, 40, 40, 40, 15, 60),
                (K.SKY_NAVIGATION, 1),
                20,
                (V.MISSILES, V.RITES),
            ),
            frame((F.FLYING_CARRIAGE, "Flying carriage", D.AIR, Y.AIRSHIP, P.MAGIC, Z.MEDIUM), (70, 50, 30, 2, 6, 35, 5, 30), (K.MAGIC, 3), 25),
            frame(
                (F.AEROPLANE, "Aeroplane", D.AIR, Y.AIRCRAFT, P.COMBUSTION, Z.MEDIUM),
                (100, 90, 40, 2, 4, 50, 10, 40),
                (K.SKY_NAVIGATION, 4),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.ROTORCRAFT, "Rotorcraft", D.AIR, Y.ROTORCRAFT, P.COMBUSTION, Z.MEDIUM),
                (80, 60, 40, 2, 10, 45, 15, 40),
                (K.SKY_NAVIGATION, 5),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.FLYING_CAR, "Flying car", D.AIR, Y.AIRCRAFT, P.ELECTRIC, Z.SMALL),
                (110, 70, 20, 1, 3, 50, 5, 30),
                (K.SKY_NAVIGATION, 6),
            ),
            frame(
                (F.FLYING_CONSTRUCT, "Flying construct", D.AIR, Y.CONSTRUCT, P.MAGIC, Z.LARGE),
                (60, 50, 30, 1, 6, 55, 40, 70),
                (K.MAGIC, 4),
                30,
                (V.RAMS, V.RITES),
            ),
            frame(
                (F.ORBITAL_LANDER, "Orbital lander", D.SPACE, Y.SPACECRAFT, P.REACTION, Z.MEDIUM),
                (40, 40, 60, 4, 10, 60, 20, 50),
                (K.VOID_LIVING, 1),
            ),
            frame((F.SHUTTLE, "Shuttle", D.SPACE, Y.SPACECRAFT, P.REACTION, Z.LARGE), (55, 70, 150, 6, 20, 65, 20, 60), (K.VOID_LIVING, 1)),
            frame(
                (F.SOLAR_SAILER, "Solar sailer", D.SPACE, Y.SPACECRAFT, P.SOLAR_SAIL, Z.LARGE),
                (90, 120, 60, 20, 10, 50, 5, 50),
                (K.SKY_NAVIGATION, 2),
                30,
            ),
            frame(
                (F.STARSHIP, "Starship", D.SPACE, Y.SPACECRAFT, P.FOLD_DRIVE, Z.HUGE),
                (80, 160, 400, 200, 150, 85, 50, 150),
                (K.VOID_LIVING, 3),
                20,
                (V.SIEGE_ENGINES, V.MISSILES),
            ),
            frame(
                (F.GENERATION_SHIP, "Generation ship", D.SPACE, Y.SPACECRAFT, P.REACTION, Z.COLOSSAL),
                (25, 200, 800, 500, 300, 80, 30, 200),
                (K.VOID_LIVING, 2),
                35,
                (V.RITES,),
            ),
            frame(
                (F.VOID_ARK, "Void ark", D.SPACE, Y.SPACECRAFT, P.MAGIC, Z.COLOSSAL),
                (35, 180, 600, 300, 400, 85, 35, 220),
                (K.VOID_LIVING, 3),
                40,
                (V.RITES,),
            ),
            frame(
                (F.CLOUD_SKIMMER, "Cloud skimmer", D.GAS_GIANT, Y.SPACECRAFT, P.REACTION, Z.LARGE),
                (60, 70, 200, 10, 10, 60, 20, 60),
                (K.VOID_LIVING, 2),
            ),
            frame(
                (F.AEROSTAT, "Aerostat", D.GAS_GIANT, Y.AIRSHIP, P.BUOYANCY, Z.COLOSSAL),
                (10, 30, 600, 40, 200, 70, 10, 120),
                (K.VOID_LIVING, 2),
            ),
            frame(
                (F.DEEP_SUBMERSIBLE, "Deep submersible", D.UNDERWATER, Y.SUBMARINE, P.ELECTRIC, Z.MEDIUM),
                (30, 60, 40, 6, 4, 90, 40, 60),
                (K.SHIPBUILDING, 5),
            ),
            frame((F.BURROWER, "Burrower", D.UNDERGROUND, Y.BURROWER, P.COMBUSTION, Z.LARGE), (15, 40, 100, 6, 10, 80, 50, 90), (K.METALLURGY, 5)),
            frame(
                (F.PLANAR_VESSEL, "Planar vessel", D.PLANAR, Y.SPACECRAFT, P.MAGIC, Z.LARGE),
                (60, 150, 150, 30, 30, 70, 25, 80),
                (K.GATE_LORE, 3),
                60,
                (V.RITES,),
            ),
            frame((F.HOVERCRAFT, "Hovercraft", D.AMPHIBIOUS, Y.MOTOR, P.COMBUSTION, Z.MEDIUM), (70, 60, 60, 3, 20, 50, 10, 40), (K.METALLURGY, 5)),
            frame(
                (F.AMPHIBIOUS_CARRIER, "Amphibious carrier", D.AMPHIBIOUS, Y.TRACKED, P.COMBUSTION, Z.LARGE),
                (40, 50, 40, 3, 20, 60, 40, 70),
                (K.METALLURGY, 5),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.LANDING_CRAFT, "Landing craft", D.AMPHIBIOUS, Y.BOAT, P.COMBUSTION, Z.MEDIUM),
                (35, 40, 80, 4, 40, 40, 15, 40),
                (K.SHIPBUILDING, 4),
            ),
            frame((F.AMPHIBIOUS_RAFT, "Amphibious raft", D.AMPHIBIOUS, Y.BOAT, P.CREW, Z.SMALL), (15, 15, 20, 2, 4, 20, 0, 10), (None, 0)),
            frame((F.TUNNEL_CART, "Tunnel cart", D.UNDERGROUND, Y.CART, P.DRAFT_ANIMALS, Z.SMALL), (15, 20, 30, 1, 0, 30, 0, 15), (None, 0)),
            frame((F.MINE_TRAIN, "Mine train", D.UNDERGROUND, Y.RAIL, P.STEAM, Z.LARGE), (25, 40, 150, 3, 10, 50, 10, 50), (K.METALLURGY, 3)),
            frame(
                (F.DELVING_CONSTRUCT, "Delving construct", D.UNDERGROUND, Y.CONSTRUCT, P.MAGIC, Z.LARGE),
                (20, 30, 50, 1, 4, 60, 40, 70),
                (K.MAGIC, 3),
                30,
                armament=(V.RAMS,),
            ),
            frame(
                (F.DEEP_CRAWLER, "Deep crawler", D.UNDERGROUND, Y.TRACKED, P.ELECTRIC, Z.LARGE),
                (20, 60, 80, 4, 10, 70, 40, 80),
                (K.METALLURGY, 6),
            ),
            frame((F.DIVING_BELL, "Diving bell", D.UNDERWATER, Y.SUBMARINE, P.TOWED, Z.SMALL), (5, 10, 10, 2, 0, 40, 10, 20), (K.SEAFARING, 2)),
            frame(
                (F.ATTACK_SUBMARINE, "Attack submarine", D.UNDERWATER, Y.SUBMARINE, P.REACTION, Z.LARGE),
                (55, 140, 40, 100, 20, 85, 40, 90),
                (K.SHIPBUILDING, 6),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.GAS_HARVESTER, "Gas harvester", D.GAS_GIANT, Y.AIRSHIP, P.REACTION, Z.HUGE),
                (20, 40, 500, 20, 10, 70, 20, 100),
                (K.VOID_LIVING, 2),
            ),
            frame(
                (F.DEEP_DIVER, "Deep diver", D.GAS_GIANT, Y.SPACECRAFT, P.REACTION, Z.MEDIUM),
                (60, 50, 40, 4, 4, 80, 30, 60),
                (K.VOID_LIVING, 3),
            ),
            frame((F.RIFT_SKIFF, "Rift skiff", D.PLANAR, Y.SPACECRAFT, P.MAGIC, Z.SMALL), (70, 80, 20, 4, 4, 50, 5, 30), (K.GATE_LORE, 1), 40),
            frame(
                (F.PLANAR_ARK, "Planar ark", D.PLANAR, Y.SPACECRAFT, P.MAGIC, Z.COLOSSAL),
                (25, 200, 500, 200, 400, 80, 30, 200),
                (K.GATE_LORE, 4),
                60,
                armament=(V.RITES,),
            ),
            frame(
                (F.DIVINE_VESSEL, "Divine vessel", D.PLANAR, Y.SPACECRAFT, P.DIVINE, Z.LARGE),
                (80, 200, 100, 10, 20, 90, 40, 100),
                (K.GATE_LORE, 5),
                80,
                armament=(V.RITES,),
            ),
            frame(
                (F.SPACE_FIGHTER, "Space fighter", D.SPACE, Y.SPACECRAFT, P.REACTION, Z.SMALL),
                (120, 60, 5, 1, 1, 40, 15, 30),
                (K.VOID_LIVING, 2),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.FREIGHTER, "Freighter", D.SPACE, Y.SPACECRAFT, P.REACTION, Z.HUGE),
                (50, 140, 1000, 20, 20, 70, 20, 120),
                (K.VOID_LIVING, 1),
            ),
            frame(
                (F.MINING_BARGE, "Mining barge", D.SPACE, Y.SPACECRAFT, P.REACTION, Z.LARGE),
                (30, 80, 600, 15, 1, 70, 30, 100),
                (K.VOID_LIVING, 1),
            ),
            frame(
                (F.CORVETTE, "Corvette", D.SPACE, Y.SPACECRAFT, P.FOLD_DRIVE, Z.LARGE),
                (90, 140, 60, 40, 30, 75, 40, 90),
                (K.VOID_LIVING, 2),
                armament=(V.MISSILES, V.SIEGE_ENGINES),
            ),
            frame(
                (F.DREADNOUGHT, "Dreadnought", D.SPACE, Y.SPACECRAFT, P.FOLD_DRIVE, Z.COLOSSAL),
                (40, 180, 300, 2000, 1000, 95, 90, 300),
                (K.VOID_LIVING, 4),
                armament=(V.SIEGE_ENGINES, V.MISSILES),
            ),
            frame(
                (F.JET_FIGHTER, "Jet fighter", D.AIR, Y.AIRCRAFT, P.COMBUSTION, Z.SMALL),
                (160, 80, 5, 1, 1, 45, 15, 35),
                (K.SKY_NAVIGATION, 5),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.BOMBER, "Bomber", D.AIR, Y.AIRCRAFT, P.COMBUSTION, Z.LARGE),
                (90, 120, 100, 6, 1, 55, 20, 60),
                (K.SKY_NAVIGATION, 5),
                armament=(V.SIEGE_ENGINES,),
            ),
            frame(
                (F.DRONE, "Drone", D.AIR, Y.AIRCRAFT, P.ELECTRIC, Z.SMALL),
                (90, 50, 5, 1, 1, 40, 0, 10),
                (K.SKY_NAVIGATION, 6),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.TRIREME, "Trireme", D.WATER, Y.GALLEY, P.SAIL_AND_OAR, Z.LARGE),
                (55, 40, 40, 170, 30, 40, 15, 50),
                (K.SEAFARING, 1),
                armament=(V.RAMS,),
            ),
            frame(
                (F.COASTAL_TRADER, "Coastal trader", D.WATER, Y.SAILING_SHIP, P.SAIL, Z.MEDIUM),
                (45, 60, 150, 20, 10, 50, 5, 40),
                (K.SEAFARING, 1),
            ),
            frame((F.CATAMARAN, "Catamaran", D.WATER, Y.BOAT, P.SAIL, Z.MEDIUM), (60, 70, 40, 8, 10, 50, 0, 25), (K.SEAFARING, 1)),
            frame(
                (F.FLEET_CARRIER, "Fleet carrier", D.WATER, Y.STEAM_SHIP, P.COMBUSTION, Z.COLOSSAL),
                (45, 120, 300, 2000, 500, 85, 60, 180),
                (K.SHIPBUILDING, 6),
                armament=(V.MISSILES,),
            ),
            frame(
                (F.HOVER_TANK, "Hover tank", D.LAND, Y.TRACKED, P.ELECTRIC, Z.LARGE),
                (80, 80, 20, 4, 6, 70, 80, 110),
                (K.METALLURGY, 7),
                armament=(V.SIEGE_ENGINES,),
            ),
        )
    },
)
SEA_LADDER = (F.SHIP_OF_THE_LINE, F.GALLEON, F.CARRACK, F.WARSHIP, F.COG, F.GALLEY, F.LONGSHIP, F.SAILBOAT, F.BOAT, F.RAFT)
SIZE_SCALE: MappingProxyType[VehicleSize, int] = total(VehicleSize, {Z.SMALL: 1, Z.MEDIUM: 2, Z.LARGE: 3, Z.HUGE: 4, Z.COLOSSAL: 5})
FAMILY_TECHNIQUES: MappingProxyType[VehicleFamily, Technique | None] = total(
    VehicleFamily,
    {
        VehicleFamily.MOUNT: None,
        VehicleFamily.CART: None,
        VehicleFamily.WAGON: None,
        VehicleFamily.CHARIOT: Technique.BRONZE,
        VehicleFamily.MOTOR: Technique.STEEL,
        VehicleFamily.TRACKED: Technique.STEEL,
        VehicleFamily.WALKER: Technique.STEEL,
        VehicleFamily.RAIL: Technique.STEEL,
        VehicleFamily.RAM: Technique.SIEGECRAFT,
        VehicleFamily.TOWER: Technique.SIEGECRAFT,
        VehicleFamily.THROWER: Technique.SIEGECRAFT,
        VehicleFamily.GUN: Technique.IRON,
        VehicleFamily.BOAT: None,
        VehicleFamily.GALLEY: Technique.SAILING,
        VehicleFamily.SAILING_SHIP: Technique.SHIPWRIGHTING,
        VehicleFamily.STEAM_SHIP: Technique.SHIPWRIGHTING,
        VehicleFamily.SUBMARINE: Technique.SHIPWRIGHTING,
        VehicleFamily.BALLOON: Technique.SKY_SAILING,
        VehicleFamily.AIRSHIP: Technique.SKY_SAILING,
        VehicleFamily.AIRCRAFT: Technique.SKY_SAILING,
        VehicleFamily.ROTORCRAFT: Technique.SKY_SAILING,
        VehicleFamily.SPACECRAFT: Technique.ASTRONOMY_INSTRUMENTS,
        VehicleFamily.BURROWER: Technique.STEEL,
        VehicleFamily.CONSTRUCT: Technique.ALCHEMY,
        VehicleFamily.LIVING: Technique.SELECTIVE_BREEDING,
    },
)
