from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.vehicles import FireControl, MountArc, VehicleSection

FIRE_CONTROL = total(
    FireControl,
    {
        FireControl.MANUAL: Defined(
            "By hand",
            checked_by=(),
            used_by=("db.tables.collective.DesignRow", "engine.collective.designs.FIRE_ORDER", "engine.collective.designs.draw_design"),
        ),
        FireControl.DRILLED: Defined("Drilled crews", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
        FireControl.SIGHTED: Defined("Sighted", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
        FireControl.DIRECTED: Defined("Directed", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
        FireControl.COMPUTED: Defined("Computed", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
        FireControl.AUTOMATIC: Defined("Automatic", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
        FireControl.GUIDED: Defined("Guided", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
    },
)

MOUNT_ARC = total(
    MountArc,
    {
        MountArc.FORWARD: Defined("Forward", checked_by=(), used_by=("engine.collective.designs.MOUNT_ARCS",)),
        MountArc.AFT: Defined("Aft", checked_by=(), used_by=("engine.collective.designs.MOUNT_ARCS",)),
        MountArc.SIDE: Defined("Sides", checked_by=(), used_by=("engine.collective.designs.MOUNT_ARCS",)),
        MountArc.ALL_ROUND: Defined(
            "All round", checked_by=("engine.vehicles.fixups.rearm",), used_by=("db.tables.vehicles.DesignMountRow", "engine.collective.designs.MOUNT_ARCS")
        ),
    },
)

VEHICLE_SECTION = total(
    VehicleSection,
    {
        VehicleSection.HULL: Defined(
            "Hull",
            checked_by=(),
            used_by=(
                "catalog.operations.SHOT_TARGETS",
                "catalog.vehicles.LAYOUTS",
                "engine.collective.designs.MOUNT_FALLBACKS",
                "engine.collective.designs.MOUNT_SECTIONS",
                "engine.operations.sail.HULL_SECTIONS",
            ),
        ),
        VehicleSection.KEEL: Defined(
            "Keel", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS", "engine.operations.sail.HULL_SECTIONS")
        ),
        VehicleSection.DECK: Defined(
            "Deck",
            checked_by=(),
            used_by=(
                "catalog.operations.SHOT_TARGETS",
                "catalog.vehicles.LAYOUTS",
                "engine.collective.designs.MOUNT_FALLBACKS",
                "engine.collective.designs.MOUNT_SECTIONS",
            ),
        ),
        VehicleSection.BOW: Defined(
            "Bow",
            checked_by=(),
            used_by=(
                "catalog.operations.RAKED_SECTIONS",
                "catalog.operations.SHOT_TARGETS",
                "catalog.vehicles.LAYOUTS",
                "engine.collective.designs.MOUNT_SECTIONS",
                "engine.operations.sail.HULL_SECTIONS",
            ),
        ),
        VehicleSection.STERN: Defined(
            "Stern",
            checked_by=(),
            used_by=(
                "catalog.operations.RAKED_SECTIONS",
                "catalog.operations.SHOT_TARGETS",
                "catalog.vehicles.LAYOUTS",
                "engine.collective.designs.MOUNT_SECTIONS",
                "engine.operations.sail.HULL_SECTIONS",
            ),
        ),
        VehicleSection.HOLD: Defined(
            "Hold", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS", "engine.operations.sail.HULL_SECTIONS")
        ),
        VehicleSection.CARGO_BAY: Defined("Cargo bay", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_SECTIONS")),
        VehicleSection.TROOP_BAY: Defined("Troop bay", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.CREW_QUARTERS: Defined("Crew quarters", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.BRIDGE: Defined("Bridge", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.COCKPIT: Defined("Cockpit", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.MAST: Defined("Mast", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.RIGGING: Defined("Rigging", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.SAILS: Defined(
            "Sails", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS", "catalog.vehicles.PROPULSION_SECTIONS")
        ),
        VehicleSection.OARS: Defined(
            "Oars",
            checked_by=("engine.operations.sail.oared",),
            used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS", "catalog.vehicles.section_swap"),
        ),
        VehicleSection.RUDDER: Defined("Rudder", checked_by=(), used_by=("catalog.operations.RAKED_SECTIONS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.STEERING: Defined("Steering", checked_by=(), used_by=("catalog.operations.RAKED_SECTIONS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.ENGINE: Defined(
            "Engine", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS", "catalog.vehicles.PROPULSION_SECTIONS")
        ),
        VehicleSection.BOILER: Defined("Boiler", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.FUEL_STORE: Defined("Fuel store", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.POWER_CORE: Defined("Power core", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.DRIVE: Defined("Drive", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.WHEELS: Defined("Wheels", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "catalog.vehicles.section_swap")),
        VehicleSection.AXLE: Defined("Axle", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.TRACKS: Defined("Tracks", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.LEGS: Defined("Legs", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.CHASSIS: Defined("Chassis", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_FALLBACKS")),
        VehicleSection.FRAME: Defined("Frame", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_FALLBACKS")),
        VehicleSection.HARNESS: Defined("Harness", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.DRAFT_TEAM: Defined("Draft team", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.SADDLE: Defined("Saddle", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_SECTIONS")),
        VehicleSection.MOUNT_BODY: Defined("Mount body", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_FALLBACKS")),
        VehicleSection.ARMOUR_PLATING: Defined(
            "Armour plating", checked_by=("engine.operations.sail.modern_shot",), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")
        ),
        VehicleSection.BARDING: Defined("Barding", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.TURRET: Defined(
            "Turret",
            checked_by=(),
            used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_FALLBACKS", "engine.collective.designs.MOUNT_SECTIONS"),
        ),
        VehicleSection.GUN_DECK: Defined(
            "Gun deck",
            checked_by=(),
            used_by=(
                "catalog.operations.RAKED_SECTIONS",
                "catalog.operations.SHOT_TARGETS",
                "catalog.vehicles.LAYOUTS",
                "engine.collective.designs.MOUNT_SECTIONS",
            ),
        ),
        VehicleSection.HARDPOINT: Defined("Hardpoint", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_SECTIONS")),
        VehicleSection.MAGAZINE: Defined("Magazine", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.WINGS: Defined(
            "Wings", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_SECTIONS")
        ),
        VehicleSection.ENVELOPE: Defined("Envelope", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.GONDOLA: Defined("Gondola", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_FALLBACKS")),
        VehicleSection.ROTOR: Defined("Rotor", checked_by=(), used_by=("catalog.operations.SHOT_TARGETS", "catalog.vehicles.LAYOUTS")),
        VehicleSection.TAIL: Defined("Tail", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.BALLAST: Defined("Ballast", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.LIFE_SUPPORT: Defined("Life support", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.AIRLOCK: Defined("Airlock", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.SENSORS: Defined("Sensors", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.NAVIGATION: Defined("Navigation", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.WARD: Defined("Ward", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_SECTIONS")),
        VehicleSection.ARM: Defined("Arm", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.COUNTERWEIGHT: Defined("Counterweight", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.RAM_HEAD: Defined("Ram head", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_SECTIONS")),
        VehicleSection.TOWER: Defined("Tower", checked_by=(), used_by=("catalog.vehicles.LAYOUTS",)),
        VehicleSection.PLATFORM: Defined(
            "Platform",
            checked_by=(),
            used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_FALLBACKS", "engine.collective.designs.MOUNT_SECTIONS"),
        ),
        VehicleSection.CORE: Defined("Core", checked_by=(), used_by=("catalog.vehicles.LAYOUTS", "engine.collective.designs.MOUNT_FALLBACKS")),
    },
)
