import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from aerona.cartography.noise import FloatArray, ValueNoise
from aerona.cartography.world_types import TerrainShape, world_type_profile
from aerona.constants.cartography import (
    CONTINENT_OCTAVES,
    CONTINENT_SCALE,
    CONTINENT_SEED_SUFFIX,
    CONTINENT_WEIGHT,
    DETAIL_OCTAVES,
    DETAIL_SCALE,
    DETAIL_WEIGHT,
    ELEVATION_SEED_SUFFIX,
    MOISTURE_OCTAVES,
    MOISTURE_SCALE,
    MOISTURE_SEED_SUFFIX,
    NOISE_OFFSET_RANGE,
    OFFSET_SEED_SUFFIX,
    RELIEF_SCALE,
    RELIEF_WEIGHT,
    SAMPLE_SEED_SUFFIX,
    SEA_SAMPLE_ORIGIN_X,
    SEA_SAMPLE_ORIGIN_Y,
    SEA_SAMPLE_SPAN_X,
    SEA_SAMPLE_SPAN_Y,
    WORLD_CENTRE_X,
    WORLD_CENTRE_Y,
)
from aerona.constants.units import PERCENT
from aerona.core.keyed_random import fnv1a32, keyed_random
from aerona.domain.enums.world import WorldType
from aerona.rules.registry import Rules
from aerona.rules.registry.world_terrain import WorldTerrainRules


class TerrainOverrides(BaseModel):
    model_config = ConfigDict(frozen=True)

    sea_pct: int | None = None
    mountains_pct: int | None = None
    moisture_pct: int | None = None


@dataclass(frozen=True)
class TerrainSettings:
    sea_fraction: float
    mountainousness: float
    moisture_offset: float
    shape: TerrainShape


def _defaults(world_type: WorldType, terrain: WorldTerrainRules) -> tuple[int, int, int]:
    table: dict[WorldType, tuple[int, int, int]] = {
        WorldType.ORDINARY: (terrain.ordinary_sea_pct, terrain.ordinary_mountains_pct, terrain.ordinary_moisture_pct),
        WorldType.OCEAN: (terrain.ocean_sea_pct, terrain.ocean_mountains_pct, terrain.ocean_moisture_pct),
        WorldType.SAND: (terrain.sand_sea_pct, terrain.sand_mountains_pct, terrain.sand_moisture_pct),
        WorldType.ICE: (terrain.ice_sea_pct, terrain.ice_mountains_pct, terrain.ice_moisture_pct),
        WorldType.LAVA: (terrain.lava_sea_pct, terrain.lava_mountains_pct, terrain.lava_moisture_pct),
        WorldType.CRYSTAL: (terrain.crystal_sea_pct, terrain.crystal_mountains_pct, terrain.crystal_moisture_pct),
        WorldType.LIVING: (terrain.living_sea_pct, terrain.living_mountains_pct, terrain.living_moisture_pct),
        WorldType.DEAD: (terrain.dead_sea_pct, terrain.dead_mountains_pct, terrain.dead_moisture_pct),
        WorldType.DREAM: (terrain.dream_sea_pct, terrain.dream_mountains_pct, terrain.dream_moisture_pct),
        WorldType.MIRROR: (terrain.mirror_sea_pct, terrain.mirror_mountains_pct, terrain.mirror_moisture_pct),
        WorldType.GAS: (terrain.gas_sea_pct, terrain.gas_mountains_pct, terrain.gas_moisture_pct),
        WorldType.RINGED: (terrain.ringed_sea_pct, terrain.ringed_mountains_pct, terrain.ringed_moisture_pct),
        WorldType.ASTEROID_BELT: (terrain.asteroid_belt_sea_pct, terrain.asteroid_belt_mountains_pct, terrain.asteroid_belt_moisture_pct),
        WorldType.TIDALLY_LOCKED: (terrain.tidally_locked_sea_pct, terrain.tidally_locked_mountains_pct, terrain.tidally_locked_moisture_pct),
        WorldType.VOID_POCKET: (terrain.void_pocket_sea_pct, terrain.void_pocket_mountains_pct, terrain.void_pocket_moisture_pct),
        WorldType.GODS_PALACE: (terrain.gods_palace_sea_pct, terrain.gods_palace_mountains_pct, terrain.gods_palace_moisture_pct),
        WorldType.GENERATION_SHIP: (terrain.generation_ship_sea_pct, terrain.generation_ship_mountains_pct, terrain.generation_ship_moisture_pct),
        WorldType.CORPSE_WORLD: (terrain.corpse_world_sea_pct, terrain.corpse_world_mountains_pct, terrain.corpse_world_moisture_pct),
        WorldType.FORGE: (terrain.forge_sea_pct, terrain.forge_mountains_pct, terrain.forge_moisture_pct),
        WorldType.SUPER_EARTH: (terrain.super_earth_sea_pct, terrain.super_earth_mountains_pct, terrain.super_earth_moisture_pct),
        WorldType.ICE_GIANT: (terrain.ice_giant_sea_pct, terrain.ice_giant_mountains_pct, terrain.ice_giant_moisture_pct),
        WorldType.HOT_GIANT: (terrain.hot_giant_sea_pct, terrain.hot_giant_mountains_pct, terrain.hot_giant_moisture_pct),
        WorldType.IRON: (terrain.iron_sea_pct, terrain.iron_mountains_pct, terrain.iron_moisture_pct),
        WorldType.CARBON: (terrain.carbon_sea_pct, terrain.carbon_mountains_pct, terrain.carbon_moisture_pct),
        WorldType.GREENHOUSE: (terrain.greenhouse_sea_pct, terrain.greenhouse_mountains_pct, terrain.greenhouse_moisture_pct),
        WorldType.DWARF_PLANET: (terrain.dwarf_planet_sea_pct, terrain.dwarf_planet_mountains_pct, terrain.dwarf_planet_moisture_pct),
        WorldType.CHTHONIAN: (terrain.chthonian_sea_pct, terrain.chthonian_mountains_pct, terrain.chthonian_moisture_pct),
        WorldType.HYCEAN: (terrain.hycean_sea_pct, terrain.hycean_mountains_pct, terrain.hycean_moisture_pct),
        WorldType.JUNGLE: (terrain.jungle_sea_pct, terrain.jungle_mountains_pct, terrain.jungle_moisture_pct),
        WorldType.FUNGAL: (terrain.fungal_sea_pct, terrain.fungal_mountains_pct, terrain.fungal_moisture_pct),
        WorldType.SHATTERED: (terrain.shattered_sea_pct, terrain.shattered_mountains_pct, terrain.shattered_moisture_pct),
        WorldType.HOLLOW: (terrain.hollow_sea_pct, terrain.hollow_mountains_pct, terrain.hollow_moisture_pct),
        WorldType.ICE_SHELL: (terrain.ice_shell_sea_pct, terrain.ice_shell_mountains_pct, terrain.ice_shell_moisture_pct),
        WorldType.METHANE: (terrain.methane_sea_pct, terrain.methane_mountains_pct, terrain.methane_moisture_pct),
    }
    return table[world_type]


def default_terrain(world_type: WorldType, rules: Rules) -> TerrainOverrides:
    sea, mountains, moisture = _defaults(world_type, rules.world_terrain)
    return TerrainOverrides(sea_pct=sea, mountains_pct=mountains, moisture_pct=moisture)


def terrain_settings(world_type: WorldType, overrides: TerrainOverrides, rules: Rules) -> TerrainSettings:
    sea, mountains, moisture = _defaults(world_type, rules.world_terrain)
    return TerrainSettings(
        sea_fraction=(overrides.sea_pct if overrides.sea_pct is not None else sea) / PERCENT,
        mountainousness=(overrides.mountains_pct if overrides.mountains_pct is not None else mountains) / PERCENT,
        moisture_offset=(overrides.moisture_pct if overrides.moisture_pct is not None else moisture) / PERCENT,
        shape=world_type_profile(world_type).shape,
    )


def _ridged(values: FloatArray) -> FloatArray:
    return 1 - np.abs(2 * values - 1)


class TerrainField:
    def __init__(self, seed: str, settings: TerrainSettings, rules: Rules) -> None:
        self.settings = settings
        self._shape_rules = rules.world_terrain
        self._relief = ValueNoise(fnv1a32(f"{seed}:{ELEVATION_SEED_SUFFIX}"))
        self._moisture = ValueNoise(fnv1a32(f"{seed}:{MOISTURE_SEED_SUFFIX}"))
        self._continents = ValueNoise(fnv1a32(f"{seed}:{CONTINENT_SEED_SUFFIX}"))
        offset = keyed_random(f"{seed}:{OFFSET_SEED_SUFFIX}")
        self._offset_x = offset() * NOISE_OFFSET_RANGE
        self._offset_y = offset() * NOISE_OFFSET_RANGE
        samples = self._sample_points(seed, rules.cartography.sea_level_samples)
        ordered = np.sort(self._shaped_elevation(samples[:, 0], samples[:, 1]))
        count = len(ordered)
        trim = min(rules.cartography.sea_level_sample_trim, max(0, (count - 1) // 2))
        sea_index = min(count - 1 - trim, max(trim, math.floor(count * settings.sea_fraction)))
        self.sea_level = float(ordered[sea_index])
        self.lowest = float(ordered[trim])
        self.highest = float(ordered[count - 1 - trim])

    def _sample_points(self, seed: str, count: int) -> NDArray[np.float64]:
        random = keyed_random(f"{seed}:{SAMPLE_SEED_SUFFIX}")
        points = np.empty((count, 2), dtype=np.float64)
        for index in range(count):
            points[index, 0] = SEA_SAMPLE_ORIGIN_X + random() * SEA_SAMPLE_SPAN_X
            points[index, 1] = SEA_SAMPLE_ORIGIN_Y + random() * SEA_SAMPLE_SPAN_Y
        return points

    def _relief_at(self, x: FloatArray, y: FloatArray, scale: float) -> FloatArray:
        detail_ratio = DETAIL_SCALE / RELIEF_SCALE
        broad = self._relief.fractal(x / scale + self._offset_x, y / scale + self._offset_y)
        fine = self._relief.fractal(x / (scale * detail_ratio) + self._offset_x, y / (scale * detail_ratio) + self._offset_y, DETAIL_OCTAVES)
        if self.settings.shape is TerrainShape.RIDGES:
            ridge_share = self._shape_rules.corpse_ridge_pct / PERCENT
            broad = _ridged(broad) * ridge_share + broad * (1 - ridge_share)
        return broad * RELIEF_WEIGHT + fine * DETAIL_WEIGHT

    def _base_elevation(self, x: FloatArray, y: FloatArray) -> FloatArray:
        if self.settings.shape is TerrainShape.FRAGMENTS:
            return self._relief_at(x, y, self._shape_rules.asteroid_fragment_scale) * self.settings.mountainousness
        continents = self._continents.fractal(x / CONTINENT_SCALE + self._offset_x, y / CONTINENT_SCALE + self._offset_y, CONTINENT_OCTAVES)
        return continents * CONTINENT_WEIGHT + self._relief_at(x, y, RELIEF_SCALE) * self.settings.mountainousness

    def _terminator_position(self, x: FloatArray) -> FloatArray:
        half_width = self._shape_rules.terminator_width / 2
        return np.clip((x - WORLD_CENTRE_X) / half_width, -1.0, 1.0)

    def _shaped_elevation(self, x: FloatArray, y: FloatArray) -> FloatArray:
        elevation = self._base_elevation(x, y)
        shape = self.settings.shape
        if shape is TerrainShape.TERMINATOR:
            elevation = elevation + np.maximum(self._terminator_position(x), 0.0) * self._shape_rules.terminator_ice_pct / PERCENT
        if shape is TerrainShape.TERRACES:
            elevation = np.floor(elevation * self._shape_rules.palace_terraces) / self._shape_rules.palace_terraces
        if shape is TerrainShape.HULL:
            elevation = np.floor(elevation * self._shape_rules.hull_decks) / self._shape_rules.hull_decks
        return elevation

    def _mask_strength(self, x: FloatArray, y: FloatArray) -> FloatArray | None:
        shape = self.settings.shape
        rules = self._shape_rules
        if shape is TerrainShape.FLOATING_ISLAND:
            distance = np.hypot(x - WORLD_CENTRE_X, y - WORLD_CENTRE_Y)
            return np.clip((distance - rules.void_pocket_radius) / rules.void_pocket_falloff, 0.0, 1.0)
        if shape is TerrainShape.HULL:
            outside_x = np.maximum(np.abs(x - WORLD_CENTRE_X) - rules.hull_length / 2, 0.0)
            outside_y = np.maximum(np.abs(y - WORLD_CENTRE_Y) - rules.hull_width / 2, 0.0)
            return np.clip(np.hypot(outside_x, outside_y) / rules.hull_falloff, 0.0, 1.0)
        return None

    def elevation(self, x: FloatArray, y: FloatArray) -> FloatArray:
        elevation = self._shaped_elevation(x, y)
        strength = self._mask_strength(x, y)
        if strength is None:
            return elevation
        floor = min(self.lowest, self.sea_level) - (self.highest - self.lowest)
        return elevation * (1 - strength) + floor * strength

    def moisture(self, x: FloatArray, y: FloatArray) -> FloatArray:
        moisture = self._moisture.fractal(x / MOISTURE_SCALE, y / MOISTURE_SCALE, MOISTURE_OCTAVES) + self.settings.moisture_offset
        shape = self.settings.shape
        if shape is TerrainShape.RING_BANDS:
            swing = self._shape_rules.ring_shadow_moisture_pct / PERCENT
            moisture = moisture + swing * np.cos(math.tau * y / self._shape_rules.ring_shadow_period)
        if shape is TerrainShape.TERMINATOR:
            moisture = moisture + self._terminator_position(x) * self._shape_rules.terminator_moisture_pct / PERCENT
        return moisture

    def normalized(self, elevation: FloatArray) -> FloatArray:
        above = max(self.highest - self.sea_level, np.finfo(np.float64).tiny)
        below = max(self.sea_level - self.lowest, np.finfo(np.float64).tiny)
        land = np.minimum(1.0, (elevation - self.sea_level) / above)
        water = -np.minimum(1.0, (self.sea_level - elevation) / below)
        return np.where(elevation > self.sea_level, land, water)
