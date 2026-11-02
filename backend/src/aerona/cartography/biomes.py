from enum import IntEnum

import numpy as np
from numpy.typing import NDArray

from aerona.constants.units import PERCENT
from aerona.rules.registry import Rules


class Biome(IntEnum):
    SHALLOW_WATER = 0
    DEEP_WATER = 1
    SHORE = 2
    DRY_LOWLAND = 3
    MID_LOWLAND = 4
    WET_LOWLAND = 5
    DRY_HILLS = 6
    WET_HILLS = 7
    MOUNTAINS = 8
    PEAKS = 9


def classify_biomes(elevation: NDArray[np.float64], moisture: NDArray[np.float64], water: NDArray[np.bool_], rules: Rules) -> NDArray[np.int64]:
    settings = rules.cartography
    deep = -settings.deep_water_depth_pct / PERCENT
    shore = settings.shore_elevation_pct / PERCENT
    lowland = settings.lowland_elevation_pct / PERCENT
    hills = settings.hill_elevation_pct / PERCENT
    mountains = settings.mountain_elevation_pct / PERCENT
    wet_lowland = settings.wet_lowland_moisture_pct / PERCENT
    mid_lowland = settings.mid_lowland_moisture_pct / PERCENT
    wet_hills = settings.wet_hill_moisture_pct / PERCENT
    conditions = [
        water & (elevation > deep),
        water,
        elevation < shore,
        (elevation < lowland) & (moisture > wet_lowland),
        (elevation < lowland) & (moisture > mid_lowland),
        elevation < lowland,
        (elevation < hills) & (moisture > wet_hills),
        elevation < hills,
        elevation < mountains,
    ]
    choices = [
        Biome.SHALLOW_WATER,
        Biome.DEEP_WATER,
        Biome.SHORE,
        Biome.WET_LOWLAND,
        Biome.MID_LOWLAND,
        Biome.DRY_LOWLAND,
        Biome.WET_HILLS,
        Biome.DRY_HILLS,
        Biome.MOUNTAINS,
    ]
    return np.select(conditions, [int(choice) for choice in choices], default=int(Biome.PEAKS)).astype(np.int64)
