from types import MappingProxyType

from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.vehicles import VehicleDomain, VehicleFamily

CARRIERS: MappingProxyType[TradeMode, tuple[frozenset[VehicleDomain], frozenset[VehicleFamily]]] = MappingProxyType(
    {
        TradeMode.ROAD: (
            frozenset({VehicleDomain.LAND}),
            frozenset({VehicleFamily.MOUNT, VehicleFamily.CART, VehicleFamily.WAGON, VehicleFamily.MOTOR, VehicleFamily.RAIL, VehicleFamily.CONSTRUCT}),
        ),
        TradeMode.RIVER: (frozenset({VehicleDomain.WATER}), frozenset({VehicleFamily.BOAT, VehicleFamily.GALLEY, VehicleFamily.STEAM_SHIP})),
        TradeMode.SEA: (
            frozenset({VehicleDomain.WATER}),
            frozenset({VehicleFamily.SAILING_SHIP, VehicleFamily.STEAM_SHIP, VehicleFamily.GALLEY, VehicleFamily.BOAT, VehicleFamily.LIVING}),
        ),
        TradeMode.SKY: (frozenset({VehicleDomain.AIR}), frozenset({VehicleFamily.AIRSHIP, VehicleFamily.BALLOON, VehicleFamily.AIRCRAFT})),
        TradeMode.SPACE: (frozenset({VehicleDomain.SPACE}), frozenset()),
        TradeMode.RIFT: (frozenset({VehicleDomain.PLANAR}), frozenset()),
        TradeMode.NETWORK: (frozenset(), frozenset()),
        TradeMode.UNDERGROUND: (frozenset({VehicleDomain.LAND}), frozenset({VehicleFamily.CART, VehicleFamily.RAIL, VehicleFamily.MOUNT})),
    }
)
