from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.cosmography import RouteScope
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import JourneyIntent, TravelMechanism, TravelMedium, TravelMethod, VehicleKind
from aerona.rules.registry import Rules

M = TravelMethod


@dataclass(frozen=True)
class TravelMethodSpec:
    method: TravelMethod
    label: str
    required_branch: KnowledgeBranch | None
    required_vehicle: VehicleKind | None
    price: str
    duration: Callable[[Rules], int]
    danger: Callable[[Rules], int]


@dataclass(frozen=True)
class TravelMethodProfile:
    method: TravelMethod
    label: str
    required_branch: KnowledgeBranch | None
    required_vehicle: VehicleKind | None
    price: str
    duration_epochs: int
    danger: int


TRAVEL_METHODS: dict[TravelMethod, TravelMethodSpec] = {
    spec.method: spec
    for spec in (
        TravelMethodSpec(
            M.ANCIENT_GATE,
            "Ancient gate",
            KnowledgeBranch.GATE_LORE,
            VehicleKind.GATE,
            "Each opening takes a share of those who pass, by the gate rules of the world.",
            lambda rules: rules.travel_methods.ancient_gate_duration,
            lambda rules: rules.travel_methods.ancient_gate_danger,
        ),
        TravelMethodSpec(
            M.SPACE_FOLD,
            "Space folding",
            KnowledgeBranch.PATHFINDING,
            None,
            "Uses up the cosmic travel resource.",
            lambda rules: rules.travel_methods.space_fold_duration,
            lambda rules: rules.travel_methods.space_fold_danger,
        ),
        TravelMethodSpec(
            M.LIGHT_SAIL,
            "Light sail",
            KnowledgeBranch.SHIPBUILDING,
            VehicleKind.SHIP,
            "Slow but free; the sail snaps if its star dies.",
            lambda rules: rules.travel_methods.light_sail_duration,
            lambda rules: rules.travel_methods.light_sail_danger,
        ),
        TravelMethodSpec(
            M.CARRIER_MOUNT,
            "Ridden crossing",
            None,
            VehicleKind.MOUNT,
            "A creature able to cross between worlds must be tamed first.",
            lambda rules: rules.travel_methods.cosmic_mount_duration,
            lambda rules: rules.travel_methods.cosmic_mount_danger,
        ),
        TravelMethodSpec(
            M.DREAM_JOURNEY,
            "Dream journey",
            KnowledgeBranch.MAGIC,
            None,
            "The body stays while the traveller goes; some never return.",
            lambda rules: rules.travel_methods.dream_journey_duration,
            lambda rules: rules.travel_methods.dream_journey_danger,
        ),
        TravelMethodSpec(
            M.DEATH_CURRENT,
            "Crossing of the dead",
            None,
            None,
            "The living who take it pay with their memories.",
            lambda rules: rules.travel_methods.river_of_dead_duration,
            lambda rules: rules.travel_methods.river_of_dead_danger,
        ),
        TravelMethodSpec(
            M.DIVINE_BRIDGE,
            "Divine bridge",
            None,
            VehicleKind.BRIDGE,
            "Collapses if the god who built it sleeps or dies.",
            lambda rules: rules.travel_methods.divine_bridge_duration,
            lambda rules: rules.travel_methods.divine_bridge_danger,
        ),
        TravelMethodSpec(
            M.SLINGSHOT_ORBIT,
            "Slingshot orbit",
            KnowledgeBranch.SKY_NAVIGATION,
            VehicleKind.SHIP,
            "Opens only in epochs when the planets align.",
            lambda rules: rules.travel_methods.slingshot_orbit_duration,
            lambda rules: rules.travel_methods.slingshot_orbit_danger,
        ),
        TravelMethodSpec(
            M.CARRIED_WITHIN,
            "Carried within a being",
            None,
            None,
            "Travellers are carried inside a being that crosses between worlds; it may not let them out.",
            lambda rules: rules.travel_methods.swallowed_duration,
            lambda rules: rules.travel_methods.swallowed_danger,
        ),
        TravelMethodSpec(
            M.WORMHOLE,
            "Wormhole",
            KnowledgeBranch.ASTRONOMY,
            VehicleKind.SHIP,
            "A natural tunnel through the void; its throat opens and shuts on its own and can close on a ship.",
            lambda rules: rules.travel_methods.wormhole_duration,
            lambda rules: rules.travel_methods.wormhole_danger,
        ),
        TravelMethodSpec(
            M.VOID_ARK,
            "Void ark",
            KnowledgeBranch.SKY_NAVIGATION,
            VehicleKind.SHIP,
            "Takes generations; the ark carries whole communities and their stores across the space between galaxies.",
            lambda rules: rules.travel_methods.void_ark_duration,
            lambda rules: rules.travel_methods.void_ark_danger,
        ),
        TravelMethodSpec(
            M.GALACTIC_GATE,
            "Galactic gate",
            KnowledgeBranch.GATE_LORE,
            VehicleKind.GATE,
            "A gate pair between galaxies, built by gods or ancient makers; it wears with use and must be mended.",
            lambda rules: rules.travel_methods.galactic_gate_duration,
            lambda rules: rules.travel_methods.galactic_gate_danger,
        ),
        TravelMethodSpec(
            M.FILAMENT_LANE,
            "Filament lane",
            KnowledgeBranch.SKY_NAVIGATION,
            None,
            "A natural road along a filament of galaxies, open to mounts and arks.",
            lambda rules: rules.travel_methods.filament_lane_duration,
            lambda rules: rules.travel_methods.filament_lane_danger,
        ),
        TravelMethodSpec(
            M.DIMENSIONAL_RIFT,
            "Dimensional rift",
            None,
            None,
            "Passes through a rift into another dimension; it shuts when the rift seals or collapses.",
            lambda rules: rules.travel_methods.dimensional_rift_duration,
            lambda rules: rules.travel_methods.dimensional_rift_danger,
        ),
        TravelMethodSpec(
            M.PLANAR_DOOR,
            "Planar door",
            KnowledgeBranch.MAGIC,
            VehicleKind.GATE,
            "A steady door between dimensions, made by a rite or a god.",
            lambda rules: rules.travel_methods.planar_door_duration,
            lambda rules: rules.travel_methods.planar_door_danger,
        ),
        TravelMethodSpec(
            M.ROCKETRY,
            "Rocketry",
            KnowledgeBranch.SKY_NAVIGATION,
            VehicleKind.SHIP,
            "Rockets built by a realm's programme; they leave only when the worlds come round to each other.",
            lambda rules: rules.travel_methods.rocketry_duration,
            lambda rules: rules.travel_methods.rocketry_danger,
        ),
    )
}

D = TravelMedium
K = TravelMechanism
TRAVEL_MODEL: Mapping[TravelMethod, tuple[TravelMedium, TravelMechanism]] = total(
    TravelMethod,
    {
        M.ANCIENT_GATE: (D.SPACE, K.GATE),
        M.SPACE_FOLD: (D.SPACE, K.FOLD),
        M.LIGHT_SAIL: (D.SPACE, K.SAIL),
        M.CARRIER_MOUNT: (D.SPACE, K.MOUNT),
        M.DREAM_JOURNEY: (D.DREAM, K.CURRENT),
        M.DEATH_CURRENT: (D.DEATH, K.CURRENT),
        M.DIVINE_BRIDGE: (D.DIVINE, K.BRIDGE),
        M.SLINGSHOT_ORBIT: (D.SPACE, K.ORBIT),
        M.CARRIED_WITHIN: (D.BODY, K.CARRIER_BEING),
        M.WORMHOLE: (D.SPACE, K.FOLD),
        M.VOID_ARK: (D.SPACE, K.SAIL),
        M.GALACTIC_GATE: (D.SPACE, K.GATE),
        M.FILAMENT_LANE: (D.SPACE, K.CURRENT),
        M.DIMENSIONAL_RIFT: (D.DIMENSION, K.GATE),
        M.PLANAR_DOOR: (D.DIMENSION, K.GATE),
        M.ROCKETRY: (D.SPACE, K.SAIL),
    },
)


def medium_of(method: TravelMethod) -> TravelMedium:
    return TRAVEL_MODEL[method][0]


METHOD_REACH: dict[TravelMethod, RouteScope] = {
    M.ANCIENT_GATE: RouteScope.INTERCLUSTER,
    M.SPACE_FOLD: RouteScope.INTERCLUSTER,
    M.LIGHT_SAIL: RouteScope.STELLAR,
    M.CARRIER_MOUNT: RouteScope.INTERGALACTIC,
    M.DREAM_JOURNEY: RouteScope.INTERDIMENSIONAL,
    M.DEATH_CURRENT: RouteScope.INTERDIMENSIONAL,
    M.DIVINE_BRIDGE: RouteScope.INTERCLUSTER,
    M.SLINGSHOT_ORBIT: RouteScope.STELLAR,
    M.CARRIED_WITHIN: RouteScope.INTERGALACTIC,
    M.WORMHOLE: RouteScope.INTERGALACTIC,
    M.VOID_ARK: RouteScope.INTERCLUSTER,
    M.GALACTIC_GATE: RouteScope.INTERCLUSTER,
    M.FILAMENT_LANE: RouteScope.INTERCLUSTER,
    M.DIMENSIONAL_RIFT: RouteScope.INTERDIMENSIONAL,
    M.PLANAR_DOOR: RouteScope.INTERDIMENSIONAL,
    M.ROCKETRY: RouteScope.STELLAR,
}

JOURNEY_INTENT_LABELS: dict[JourneyIntent, str] = {
    JourneyIntent.COLONY: "Colony",
    JourneyIntent.TRADE: "Trade",
    JourneyIntent.EXPLORATION: "Exploration",
    JourneyIntent.CONQUEST: "Conquest",
    JourneyIntent.PILGRIMAGE: "Pilgrimage",
}


def travel_method_profile(rules: Rules, method: TravelMethod) -> TravelMethodProfile:
    spec = TRAVEL_METHODS[method]
    return TravelMethodProfile(method, spec.label, spec.required_branch, spec.required_vehicle, spec.price, spec.duration(rules), spec.danger(rules))


def travel_method_table(rules: Rules) -> dict[TravelMethod, TravelMethodProfile]:
    return {method: travel_method_profile(rules, method) for method in TravelMethod}
