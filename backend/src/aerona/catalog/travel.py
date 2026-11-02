from collections.abc import Callable
from dataclasses import dataclass

from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import JourneyIntent, TravelMethod, VehicleKind
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
            "Opening it demands a sacrifice or a true name.",
            lambda rules: rules.travel_methods.ancient_gate_duration,
            lambda rules: rules.travel_methods.ancient_gate_danger,
        ),
        TravelMethodSpec(
            M.SPACE_FOLD,
            "Space folding",
            KnowledgeBranch.PATHFINDING,
            None,
            "Consumes the cosmic travel resource and breeds addiction.",
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
            M.COSMIC_MOUNT,
            "Cosmic mount",
            None,
            VehicleKind.MOUNT,
            "A void creature must be tamed first.",
            lambda rules: rules.travel_methods.cosmic_mount_duration,
            lambda rules: rules.travel_methods.cosmic_mount_danger,
        ),
        TravelMethodSpec(
            M.DREAM_JOURNEY,
            "Dream journey",
            KnowledgeBranch.MAGIC,
            None,
            "The body stays and the soul goes; some never return.",
            lambda rules: rules.travel_methods.dream_journey_duration,
            lambda rules: rules.travel_methods.dream_journey_danger,
        ),
        TravelMethodSpec(
            M.RIVER_OF_DEAD,
            "River of the dead",
            None,
            None,
            "The living who sail it pay with their memories.",
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
            M.SWALLOWED,
            "Being swallowed",
            None,
            None,
            "Travellers ride inside a cosmic creature; the way out is not guaranteed.",
            lambda rules: rules.travel_methods.swallowed_duration,
            lambda rules: rules.travel_methods.swallowed_danger,
        ),
    )
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
