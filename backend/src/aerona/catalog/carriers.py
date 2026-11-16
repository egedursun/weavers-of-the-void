from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.operations import CarrierKind
from aerona.domain.enums.urban import TransportKind

K = CarrierKind
T = Technique
M = TradeMode


@dataclass(frozen=True)
class CarrierSpec:
    label: str
    capacity: int
    speed: int
    cost: int
    technique: Technique | None
    modes: frozenset[TradeMode]
    upkeep: str | None
    exposure: int


LAND = frozenset({M.ROAD, M.CARAVAN})
WATER = frozenset({M.RIVER, M.SEA})
EVERY = frozenset(TradeMode)
CARRIERS: Mapping[CarrierKind, CarrierSpec] = total(
    CarrierKind,
    {
        K.PORTERS: CarrierSpec("Porters", 1, 1, 1, None, LAND, "feed", 30),
        K.PACK_ANIMALS: CarrierSpec("Pack animals", 4, 2, 2, None, LAND, "feed", 40),
        K.ANIMAL_CARTS: CarrierSpec("Animal carts", 10, 2, 3, None, frozenset({M.ROAD}), "feed", 40),
        K.RAIL: CarrierSpec("Rail", 80, 6, 4, T.RAILWAYS, frozenset({M.ROAD}), "fuel", 20),
        K.ROAD_MOTOR: CarrierSpec("Motor transport", 30, 5, 5, T.COMBUSTION_ENGINE, LAND, "fuel", 30),
        K.RIVER_AND_CANAL: CarrierSpec("River and canal boats", 25, 3, 2, None, frozenset({M.RIVER}), None, 25),
        K.SEA: CarrierSpec("Sea ships", 60, 4, 3, T.SAILING, frozenset({M.SEA}), None, 35),
        K.AIR: CarrierSpec("Aircraft", 20, 9, 9, T.AVIATION, EVERY, "fuel", 15),
        K.PIPELINE: CarrierSpec("Pipelines", 100, 7, 2, T.INDUSTRIAL_CHEMISTRY, LAND, None, 25),
        K.ORBITAL_LIFT: CarrierSpec("Orbital lifts", 120, 8, 6, T.ROCKETRY, frozenset({M.SKY}), "fuel", 10),
        K.SPACE: CarrierSpec("Space freighters", 150, 9, 8, T.ROCKETRY, frozenset({M.SKY}), "fuel", 20),
        K.TELEPORT: CarrierSpec("Teleport", 50, 10, 10, T.ARTIFICIAL_MINDS, EVERY, None, 5),
        K.LIVING: CarrierSpec("Living carriers", 35, 4, 3, T.GENETIC_ENGINEERING, LAND | WATER, "feed", 30),
        K.RITE: CarrierSpec("Bound conveyance", 15, 8, 7, T.SUMMONING, EVERY, None, 10),
        K.NETWORK: CarrierSpec("Networks", 0, 10, 1, T.COMPUTATION, EVERY, None, 15),
    },
)
CARRIER_OF: Mapping[TransportKind, CarrierKind] = total(TransportKind, {kind: CarrierKind(kind.value) for kind in TransportKind})
