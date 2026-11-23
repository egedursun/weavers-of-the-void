from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.climes import CirculationBand
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.rules.registry import Rules

EAST = 2
WEST = 6
NORTH = 0


@dataclass(frozen=True)
class BeltSpec:
    label: str
    blows_from: int
    strength: Callable[[Rules], int]
    rain_pct: Callable[[Rules], int]
    sailing_pct: Callable[[Rules], int]
    calm: bool = False


BELTS: Mapping[CirculationBand, BeltSpec] = total(
    CirculationBand,
    {
        CirculationBand.TRADE: BeltSpec(
            "Trade winds", EAST, lambda rules: rules.winds.trade_strength, lambda rules: rules.winds.trade_rain_pct, lambda rules: rules.winds.trade_sailing_pct
        ),
        CirculationBand.WESTERLY: BeltSpec(
            "Westerlies",
            WEST,
            lambda rules: rules.winds.westerly_strength,
            lambda rules: rules.winds.westerly_rain_pct,
            lambda rules: rules.winds.westerly_sailing_pct,
        ),
        CirculationBand.POLAR: BeltSpec(
            "Polar easterlies",
            EAST,
            lambda rules: rules.winds.polar_strength,
            lambda rules: rules.winds.polar_rain_pct,
            lambda rules: rules.winds.polar_sailing_pct,
        ),
        CirculationBand.SINGLE_CELL: BeltSpec(
            "One band",
            NORTH,
            lambda rules: rules.winds.single_cell_strength,
            lambda rules: rules.winds.single_cell_rain_pct,
            lambda rules: rules.winds.single_cell_sailing_pct,
        ),
        CirculationBand.TERMINATOR: BeltSpec(
            "Terminator winds",
            EAST,
            lambda rules: rules.winds.terminator_strength,
            lambda rules: rules.winds.terminator_rain_pct,
            lambda rules: rules.winds.terminator_sailing_pct,
        ),
        CirculationBand.STILL: BeltSpec(
            "Still air",
            NORTH,
            lambda rules: rules.winds.still_strength,
            lambda rules: rules.winds.still_rain_pct,
            lambda rules: rules.winds.still_sailing_pct,
            calm=True,
        ),
        CirculationBand.DOLDRUMS: BeltSpec(
            "Doldrums",
            NORTH,
            lambda rules: rules.winds.doldrums_strength,
            lambda rules: rules.winds.doldrums_rain_pct,
            lambda rules: rules.winds.doldrums_sailing_pct,
            calm=True,
        ),
        CirculationBand.SUBTROPICAL_CALM: BeltSpec(
            "Subtropical calm",
            NORTH,
            lambda rules: rules.winds.subtropical_calm_strength,
            lambda rules: rules.winds.subtropical_calm_rain_pct,
            lambda rules: rules.winds.subtropical_calm_sailing_pct,
            calm=True,
        ),
        CirculationBand.BANDED: BeltSpec(
            "Banded winds",
            EAST,
            lambda rules: rules.winds.banded_strength,
            lambda rules: rules.winds.banded_rain_pct,
            lambda rules: rules.winds.banded_sailing_pct,
        ),
        CirculationBand.SUPER_ROTATION: BeltSpec(
            "Super rotation",
            EAST,
            lambda rules: rules.winds.super_rotation_strength,
            lambda rules: rules.winds.super_rotation_rain_pct,
            lambda rules: rules.winds.super_rotation_sailing_pct,
        ),
    },
)


@dataclass(frozen=True)
class CurrentSpec:
    label: str
    temperature: Callable[[Rules], int]
    sailing_pct: Callable[[Rules], int]
    danger: Callable[[Rules], int]


CURRENTS: Mapping[OceanCurrent, CurrentSpec] = total(
    OceanCurrent,
    {
        OceanCurrent.NONE: CurrentSpec(
            "No current", lambda rules: rules.currents.none_temperature, lambda rules: rules.currents.none_sailing_pct, lambda rules: rules.currents.none_danger
        ),
        OceanCurrent.WARM: CurrentSpec(
            "Warm current",
            lambda rules: rules.currents.warm_temperature,
            lambda rules: rules.currents.warm_sailing_pct,
            lambda rules: rules.currents.warm_danger,
        ),
        OceanCurrent.COLD: CurrentSpec(
            "Cold current",
            lambda rules: rules.currents.cold_temperature,
            lambda rules: rules.currents.cold_sailing_pct,
            lambda rules: rules.currents.cold_danger,
        ),
        OceanCurrent.UPWELLING: CurrentSpec(
            "Upwelling current",
            lambda rules: rules.currents.upwelling_temperature,
            lambda rules: rules.currents.upwelling_sailing_pct,
            lambda rules: rules.currents.upwelling_danger,
        ),
        OceanCurrent.TIDAL: CurrentSpec(
            "Tidal current",
            lambda rules: rules.currents.tidal_temperature,
            lambda rules: rules.currents.tidal_sailing_pct,
            lambda rules: rules.currents.tidal_danger,
        ),
    },
)
