from collections.abc import Mapping
from dataclasses import dataclass

from aerona.catalog.gravity import GRAVITY
from aerona.catalog.life.domain import PERIODIC_BODIES
from aerona.catalog.physics_life import AIR_NEEDS
from aerona.core.total import partial, total
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.ecology import SizeClass
from aerona.domain.enums.physics import AirNeed, CosmicFeatureKind
from aerona.domain.enums.travel import ArrivalOutcome, JourneyIntent, VehicleKind
from aerona.domain.enums.world import Atmosphere, Gravity, WorldType
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause

ARRIVALS: Mapping[JourneyIntent, ArrivalOutcome] = total(
    JourneyIntent,
    {
        JourneyIntent.COLONY: ArrivalOutcome.SETTLERS,
        JourneyIntent.TRADE: ArrivalOutcome.SETTLERS,
        JourneyIntent.EXPLORATION: ArrivalOutcome.SETTLERS,
        JourneyIntent.CONQUEST: ArrivalOutcome.INVADERS,
        JourneyIntent.PILGRIMAGE: ArrivalOutcome.SETTLERS,
        JourneyIntent.EXILE: ArrivalOutcome.SETTLERS,
        JourneyIntent.FLIGHT: ArrivalOutcome.REFUGEES,
        JourneyIntent.EMBASSY: ArrivalOutcome.SETTLERS,
        JourneyIntent.RESCUE: ArrivalOutcome.SETTLERS,
        JourneyIntent.RETURN: ArrivalOutcome.SETTLERS,
    },
)


AIR_GAS = partial(AirNeed, {need: spec.gas for need, spec in AIR_NEEDS.items() if spec.gas is not None}, without={AirNeed.NONE})


GRAVITY_G: dict[Gravity, float] = {band: spec.g for band, spec in GRAVITY.items()}


AIR: dict[Atmosphere, tuple[float, dict[str, int]]] = {
    Atmosphere.NONE: (0.0, {"nitrogen": 0, "oxygen": 0, "carbon_dioxide": 0, "methane": 0, "water_vapour": 0, "exotic_gas": 0}),
    Atmosphere.THIN: (0.3, {"nitrogen": 80, "oxygen": 16, "carbon_dioxide": 4, "methane": 0, "water_vapour": 0, "exotic_gas": 0}),
    Atmosphere.NORMAL: (1.0, {"nitrogen": 78, "oxygen": 21, "carbon_dioxide": 1, "methane": 0, "water_vapour": 0, "exotic_gas": 0}),
    Atmosphere.DENSE: (4.0, {"nitrogen": 75, "oxygen": 18, "carbon_dioxide": 5, "methane": 0, "water_vapour": 2, "exotic_gas": 0}),
    Atmosphere.TOXIC: (1.5, {"nitrogen": 40, "oxygen": 2, "carbon_dioxide": 40, "methane": 8, "water_vapour": 0, "exotic_gas": 10}),
    Atmosphere.STEAM: (6.0, {"nitrogen": 20, "oxygen": 2, "carbon_dioxide": 18, "methane": 0, "water_vapour": 60, "exotic_gas": 0}),
    Atmosphere.LAYERED: (1.2, {"nitrogen": 70, "oxygen": 14, "carbon_dioxide": 8, "methane": 2, "water_vapour": 2, "exotic_gas": 4}),
}


STAR_BOUND = frozenset({CosmicFeatureKind.ASTEROID_FIELD, CosmicFeatureKind.GRAVITY_WELL, *PERIODIC_BODIES})


GREAT_MOUNTS = (SizeClass.HUGE, SizeClass.COLOSSAL)


VEHICLE_TECHNIQUES: Mapping[VehicleKind, Technique | None] = total(
    VehicleKind,
    {
        VehicleKind.GATE: None,
        VehicleKind.SHIP: None,
        VehicleKind.MOUNT: None,
        VehicleKind.BRIDGE: None,
        VehicleKind.RAIL: Technique.RAILWAYS,
        VehicleKind.ROAD_VEHICLE: Technique.COMBUSTION_ENGINE,
        VehicleKind.AIRCRAFT: Technique.AVIATION,
        VehicleKind.TELEPORT: Technique.ARTIFICIAL_MINDS,
        VehicleKind.LIVING: Technique.GENETIC_ENGINEERING,
        VehicleKind.RIFT: None,
        VehicleKind.ON_FOOT: None,
        VehicleKind.DRIFT: None,
    },
)


CAUSE_END: Mapping[WorldEndCause, WorldEnd] = total(
    WorldEndCause,
    {
        WorldEndCause.IMPACT: WorldEnd.SHATTERED,
        WorldEndCause.DIVINE_WRATH: WorldEnd.SHATTERED,
        WorldEndCause.STAR_GIANT: WorldEnd.CONSUMED,
        WorldEndCause.STAR_DEATH: WorldEnd.FROZEN_DEAD,
        WorldEndCause.VOID: WorldEnd.SUNK_INTO_VOID,
        WorldEndCause.OBLIVION: WorldEnd.FORGOTTEN,
        WorldEndCause.BELIEF_DRIFT: WorldEnd.TRANSFIGURED,
        WorldEndCause.RUNAWAY_CLIMATE: WorldEnd.BURNED,
        WorldEndCause.WAR: WorldEnd.BURNED,
        WorldEndCause.OUTER_HUNGER: WorldEnd.DEVOURED,
        WorldEndCause.PLAGUE: WorldEnd.EMPTIED,
        WorldEndCause.RUNAWAY_MAKING: WorldEnd.CONSUMED,
        WorldEndCause.STRUCTURE_FAILURE: WorldEnd.SHATTERED,
    },
)

END_REMNANT: Mapping[WorldEnd, WorldType | None] = total(
    WorldEnd,
    {
        WorldEnd.SHATTERED: WorldType.SHATTERED,
        WorldEnd.CONSUMED: None,
        WorldEnd.FROZEN_DEAD: None,
        WorldEnd.SUNK_INTO_VOID: None,
        WorldEnd.FORGOTTEN: None,
        WorldEnd.TRANSFIGURED: None,
        WorldEnd.DROWNED: WorldType.OCEAN,
        WorldEnd.BURNED: WorldType.DEAD,
        WorldEnd.DEVOURED: WorldType.VOID_POCKET,
        WorldEnd.EMPTIED: None,
        WorldEnd.MERGED: None,
    },
)

SOURCED_CAUSES = frozenset({WorldEndCause.WAR, WorldEndCause.OUTER_HUNGER, WorldEndCause.RUNAWAY_MAKING})

END_WORLD_WORLD_ENDS = frozenset(end for end, remnant in END_REMNANT.items() if remnant is not None) | {WorldEnd.TRANSFIGURED}

LIFE_BARRING_WORLDS = frozenset({WorldType.VOID_POCKET, WorldType.ASTEROID_BELT, WorldType.SHATTERED})


@dataclass(frozen=True)
class ColonyOf:
    kind: str
    ruled: bool = True


COLONIES: Mapping[JourneyIntent, ColonyOf] = total(
    JourneyIntent,
    {
        JourneyIntent.COLONY: ColonyOf("colony"),
        JourneyIntent.TRADE: ColonyOf("colony"),
        JourneyIntent.EXPLORATION: ColonyOf("colony"),
        JourneyIntent.CONQUEST: ColonyOf("conquest outpost"),
        JourneyIntent.PILGRIMAGE: ColonyOf("colony"),
        JourneyIntent.EXILE: ColonyOf("settlement of exiles", ruled=False),
        JourneyIntent.FLIGHT: ColonyOf("refuge", ruled=False),
        JourneyIntent.EMBASSY: ColonyOf("colony"),
        JourneyIntent.RESCUE: ColonyOf("rescue camp"),
        JourneyIntent.RETURN: ColonyOf("homecoming", ruled=False),
    },
)
