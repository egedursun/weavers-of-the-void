from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.travel import RouteEnvironment, TravelMechanism, TravelMedium

ROUTE_ENVIRONMENT = total(
    RouteEnvironment,
    {
        RouteEnvironment.SEA: Defined("Sea", checked_by=(), used_by=("engine.cosmos.encounters.ENVIRONMENTS",)),
        RouteEnvironment.LAND: Defined("Land", checked_by=(), used_by=("engine.cosmos.encounters.ENVIRONMENTS",)),
        RouteEnvironment.AIR: Defined("Air", checked_by=(), used_by=("engine.cosmos.encounters.ENVIRONMENTS",)),
        RouteEnvironment.SPACE: Defined("Space", checked_by=(), used_by=("engine.cosmos.encounters.ENVIRONMENTS",)),
        RouteEnvironment.RIFT: Defined("Rift", checked_by=(), used_by=("engine.cosmos.encounters.ENVIRONMENTS",)),
        RouteEnvironment.NETWORK: Defined("Network", checked_by=(), used_by=("engine.cosmos.encounters.ENVIRONMENTS",)),
    },
)

TRAVEL_MECHANISM = total(
    TravelMechanism,
    {
        TravelMechanism.GATE: Defined("by a gate", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMechanism.FOLD: Defined("by folding the way", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMechanism.SAIL: Defined("under sail or drive", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMechanism.MOUNT: Defined("on a ridden creature", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMechanism.BRIDGE: Defined("over a bridge", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMechanism.CURRENT: Defined("on a current", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMechanism.CARRIER_BEING: Defined("within a carrier being", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMechanism.ORBIT: Defined("along an orbit", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
    },
)

TRAVEL_MEDIUM = total(
    TravelMedium,
    {
        TravelMedium.SPACE: Defined("through space", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMedium.DIMENSION: Defined("between dimensions", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMedium.DREAM: Defined("through dreams", checked_by=("engine.phases.travel.MEDIUM_EVENTS",), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMedium.DEATH: Defined(
            "through the realm of the dead",
            checked_by=("engine.cosmos.routes._passage_problem", "engine.phases.travel.MEDIUM_EVENTS", "engine.phases.travel._forget_on_crossing"),
            used_by=("catalog.travel.TRAVEL_MODEL",),
        ),
        TravelMedium.DIVINE: Defined("by divine power", checked_by=(), used_by=("catalog.travel.TRAVEL_MODEL",)),
        TravelMedium.BODY: Defined("carried inside a being", checked_by=("engine.phases.travel.MEDIUM_EVENTS",), used_by=("catalog.travel.TRAVEL_MODEL",)),
    },
)
