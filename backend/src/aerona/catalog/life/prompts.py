from aerona.core.total import total
from aerona.domain.enums.travel import VehicleKind

VESSEL_DIRECTIONS = total(
    VehicleKind,
    {
        VehicleKind.GATE: "a gate between worlds with what shows through it and travellers before it for scale",
        VehicleKind.SHIP: "a vessel between worlds with what moves it and its crew on the way it crosses",
        VehicleKind.MOUNT: "a mount carrying its rider between worlds, in motion, at a scale that shows its size",
        VehicleKind.BRIDGE: "a bridge spanning the gap between worlds, travellers crossing it",
        VehicleKind.RAIL: "a vehicle that runs on a fixed track, with its riders, at a scale that shows its size",
        VehicleKind.ROAD_VEHICLE: "a vehicle that travels over land, with its riders, at a scale that shows its size",
        VehicleKind.AIRCRAFT: "a vehicle in flight with its crew, at a scale that shows its size",
        VehicleKind.TELEPORT: "a device that sends travellers from one place to another, with travellers beside it for scale",
        VehicleKind.LIVING: "a living being that carries travellers, in motion, at a scale that shows its size",
        VehicleKind.RIFT: "an opening between places with what shows through it and travellers before it for scale",
        VehicleKind.ON_FOOT: "travellers on foot on their way, with the land they cross",
        VehicleKind.DRIFT: "a craft or body carried between worlds by a current or a drifting mass, with its passengers on it",
    },
)
