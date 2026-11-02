from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.cartography.biomes import Biome
from aerona.catalog.climate import climate_profile
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.domain.enums.environment import (
    CoastKind,
    MovementMode,
    RiverClass,
    ScarKind,
    SoilKind,
    TemperatureBand,
    TerrainKind,
)
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.world import ClimateEra, WorldType
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

WORLD_TEMPERATURE: dict[WorldType, Callable[[Rules], int]] = {
    WorldType.ORDINARY: lambda rules: rules.environment.temperature_ordinary,
    WorldType.OCEAN: lambda rules: rules.environment.temperature_ocean,
    WorldType.SAND: lambda rules: rules.environment.temperature_sand,
    WorldType.ICE: lambda rules: rules.environment.temperature_ice,
    WorldType.LAVA: lambda rules: rules.environment.temperature_lava,
    WorldType.CRYSTAL: lambda rules: rules.environment.temperature_crystal,
    WorldType.LIVING: lambda rules: rules.environment.temperature_living,
    WorldType.DEAD: lambda rules: rules.environment.temperature_dead,
    WorldType.DREAM: lambda rules: rules.environment.temperature_dream,
    WorldType.MIRROR: lambda rules: rules.environment.temperature_mirror,
    WorldType.GAS: lambda rules: rules.environment.temperature_gas,
    WorldType.RINGED: lambda rules: rules.environment.temperature_ringed,
    WorldType.ASTEROID_BELT: lambda rules: rules.environment.temperature_asteroid_belt,
    WorldType.TIDALLY_LOCKED: lambda rules: rules.environment.temperature_tidally_locked,
    WorldType.VOID_POCKET: lambda rules: rules.environment.temperature_void_pocket,
    WorldType.GODS_PALACE: lambda rules: rules.environment.temperature_gods_palace,
    WorldType.GENERATION_SHIP: lambda rules: rules.environment.temperature_generation_ship,
    WorldType.CORPSE_WORLD: lambda rules: rules.environment.temperature_corpse_world,
    WorldType.FORGE: lambda rules: rules.environment.temperature_forge,
    WorldType.SUPER_EARTH: lambda rules: rules.environment.temperature_super_earth,
    WorldType.ICE_GIANT: lambda rules: rules.environment.temperature_ice_giant,
    WorldType.HOT_GIANT: lambda rules: rules.environment.temperature_hot_giant,
    WorldType.IRON: lambda rules: rules.environment.temperature_iron,
    WorldType.CARBON: lambda rules: rules.environment.temperature_carbon,
    WorldType.GREENHOUSE: lambda rules: rules.environment.temperature_greenhouse,
    WorldType.DWARF_PLANET: lambda rules: rules.environment.temperature_dwarf_planet,
    WorldType.CHTHONIAN: lambda rules: rules.environment.temperature_chthonian,
    WorldType.HYCEAN: lambda rules: rules.environment.temperature_hycean,
    WorldType.JUNGLE: lambda rules: rules.environment.temperature_jungle,
    WorldType.FUNGAL: lambda rules: rules.environment.temperature_fungal,
    WorldType.SHATTERED: lambda rules: rules.environment.temperature_shattered,
    WorldType.HOLLOW: lambda rules: rules.environment.temperature_hollow,
    WorldType.ICE_SHELL: lambda rules: rules.environment.temperature_ice_shell,
    WorldType.METHANE: lambda rules: rules.environment.temperature_methane,
}

WORLD_TERRAIN: dict[WorldType, TerrainKind] = {
    WorldType.LAVA: TerrainKind.VOLCANIC,
    WorldType.CRYSTAL: TerrainKind.CRYSTAL_FIELD,
    WorldType.LIVING: TerrainKind.FLESH,
    WorldType.CORPSE_WORLD: TerrainKind.FLESH,
    WorldType.VOID_POCKET: TerrainKind.VOID_SHORE,
    WorldType.GENERATION_SHIP: TerrainKind.UNDERGROUND,
    WorldType.ASTEROID_BELT: TerrainKind.CANYON,
    WorldType.GREENHOUSE: TerrainKind.VOLCANIC,
    WorldType.DWARF_PLANET: TerrainKind.ICE_SHEET,
    WorldType.CHTHONIAN: TerrainKind.VOLCANIC,
    WorldType.JUNGLE: TerrainKind.JUNGLE,
    WorldType.ICE_SHELL: TerrainKind.ICE_SHEET,
    WorldType.METHANE: TerrainKind.TUNDRA,
}

WORLD_SOIL: dict[WorldType, SoilKind] = {
    WorldType.LAVA: SoilKind.VOLCANIC,
    WorldType.CRYSTAL: SoilKind.CRYSTAL,
    WorldType.DEAD: SoilKind.BONE,
    WorldType.CORPSE_WORLD: SoilKind.BONE,
    WorldType.SAND: SoilKind.SAND,
    WorldType.ICE: SoilKind.THIN,
    WorldType.ASTEROID_BELT: SoilKind.THIN,
    WorldType.VOID_POCKET: SoilKind.ASH,
    WorldType.FORGE: SoilKind.ASH,
    WorldType.IRON: SoilKind.THIN,
    WorldType.CARBON: SoilKind.ASH,
    WorldType.GREENHOUSE: SoilKind.VOLCANIC,
    WorldType.DWARF_PLANET: SoilKind.THIN,
    WorldType.CHTHONIAN: SoilKind.VOLCANIC,
    WorldType.JUNGLE: SoilKind.PEAT,
    WorldType.FUNGAL: SoilKind.PEAT,
    WorldType.SHATTERED: SoilKind.THIN,
    WorldType.ICE_SHELL: SoilKind.THIN,
    WorldType.METHANE: SoilKind.THIN,
}

WORLD_MINERALS: dict[WorldType, tuple[MaterialKind, ...]] = {
    WorldType.IRON: (MaterialKind.IRON, MaterialKind.LEAD),
    WorldType.CARBON: (MaterialKind.GEMS,),
    WorldType.GREENHOUSE: (MaterialKind.SULFUR,),
    WorldType.CHTHONIAN: (MaterialKind.IRON, MaterialKind.GOLD),
    WorldType.HYCEAN: (MaterialKind.SALT,),
    WorldType.JUNGLE: (MaterialKind.AMBER,),
    WorldType.FORGE: (MaterialKind.IRON, MaterialKind.COPPER),
    WorldType.SHATTERED: (MaterialKind.STAR_METAL,),
    WorldType.HOLLOW: (MaterialKind.GEMS,),
    WorldType.ICE_SHELL: (MaterialKind.SALT,),
}

SOIL_FERTILITY: dict[SoilKind, Callable[[Rules], int]] = {
    SoilKind.THIN: lambda rules: rules.environment.soil_thin,
    SoilKind.LOAM: lambda rules: rules.environment.soil_loam,
    SoilKind.CLAY: lambda rules: rules.environment.soil_clay,
    SoilKind.SAND: lambda rules: rules.environment.soil_sand,
    SoilKind.VOLCANIC: lambda rules: rules.environment.soil_volcanic,
    SoilKind.PEAT: lambda rules: rules.environment.soil_peat,
    SoilKind.SALT: lambda rules: rules.environment.soil_salt,
    SoilKind.ASH: lambda rules: rules.environment.soil_ash,
    SoilKind.CRYSTAL: lambda rules: rules.environment.soil_crystal,
    SoilKind.BONE: lambda rules: rules.environment.soil_bone,
}

SCAR_FERTILITY: dict[ScarKind, Callable[[Rules], int]] = {
    ScarKind.BATTLEFIELD: lambda rules: rules.scars.battlefield_fertility_pct,
    ScarKind.PLAGUE_GROUND: lambda rules: rules.scars.plague_ground_fertility_pct,
    ScarKind.SALTED_EARTH: lambda rules: rules.scars.salted_earth_fertility_pct,
    ScarKind.BURNED: lambda rules: rules.scars.burned_fertility_pct,
    ScarKind.CRATER: lambda rules: rules.scars.crater_fertility_pct,
    ScarKind.HAUNTED: lambda rules: rules.scars.haunted_fertility_pct,
    ScarKind.BLIGHTED: lambda rules: rules.scars.blighted_fertility_pct,
    ScarKind.LEAK_WOUND: lambda rules: rules.scars.leak_wound_fertility_pct,
}

RIVER_IRRIGATION: dict[RiverClass, Callable[[Rules], int]] = {
    RiverClass.NONE: lambda rules: 0,
    RiverClass.STREAM: lambda rules: rules.environment.stream_irrigation_pct,
    RiverClass.RIVER: lambda rules: rules.environment.river_irrigation_pct,
    RiverClass.GREAT_RIVER: lambda rules: rules.environment.great_river_irrigation_pct,
}

RIVER_RANK: dict[RiverClass, int] = {RiverClass.NONE: 0, RiverClass.STREAM: 1, RiverClass.RIVER: 2, RiverClass.GREAT_RIVER: 3}
RIVER_TOP_RANK = 3

MODE_SENSITIVITY: dict[MovementMode, Callable[[Rules], tuple[int, int, int, int, int]]] = {
    MovementMode.ON_FOOT: lambda rules: (
        rules.passability.foot_roughness_pct,
        rules.passability.foot_forest_pct,
        rules.passability.foot_wetland_pct,
        rules.passability.foot_river_pct,
        rules.passability.foot_cold_pct,
    ),
    MovementMode.MOUNTED: lambda rules: (
        rules.passability.mounted_roughness_pct,
        rules.passability.mounted_forest_pct,
        rules.passability.mounted_wetland_pct,
        rules.passability.mounted_river_pct,
        rules.passability.mounted_cold_pct,
    ),
    MovementMode.WHEELED: lambda rules: (
        rules.passability.wheeled_roughness_pct,
        rules.passability.wheeled_forest_pct,
        rules.passability.wheeled_wetland_pct,
        rules.passability.wheeled_river_pct,
        rules.passability.wheeled_cold_pct,
    ),
    MovementMode.BURROWING: lambda rules: (
        rules.passability.burrowing_roughness_pct,
        0,
        rules.passability.burrowing_wetland_pct,
        rules.passability.burrowing_river_pct,
        rules.passability.burrowing_cold_pct,
    ),
}


@dataclass(frozen=True)
class Surroundings:
    world_type: WorldType
    era: ClimateEra | None
    coastal: bool
    highland: bool
    ruins: int = 0
    chokepoints: int = 0
    star_heat: int = 0


@dataclass(frozen=True)
class Geography:
    biome_mix: list[int]
    elevation_mean: int
    roughness: int
    latitude: int
    moisture: int
    base_forest: int
    base_wetland: int
    river_class: RiverClass


def share(biome_mix: list[int], *biomes: Biome) -> int:
    return sum(biome_mix[biome] for biome in biomes if biome < len(biome_mix))


def temperature_of(rules: Rules, geography: Geography, around: Surroundings) -> int:
    settings = rules.environment
    value = (
        WORLD_TEMPERATURE[around.world_type](rules)
        + around.star_heat
        - geography.latitude * settings.latitude_cooling_pct / PERCENT
        - geography.elevation_mean * settings.elevation_cooling_pct / PERCENT
    )
    if around.coastal:
        value += (settings.coast_moderation_target - value) * settings.coast_moderation_pct / PERCENT
    if around.era is not None:
        value += climate_profile(rules, around.era).temperature_shift
        if around.era is ClimateEra.ICE_AGE and around.highland:
            value -= rules.climate_effects.mountain_ice_loss
    return clamp_int(value, 0, PERCENT)


def rainfall_of(rules: Rules, geography: Geography, around: Surroundings) -> int:
    settings = rules.environment
    value = geography.moisture * settings.rain_from_moisture_pct / PERCENT + (settings.coastal_rainfall if around.coastal else 0)
    if around.era is not None:
        shift = climate_profile(rules, around.era).rain_shift
        if around.era is ClimateEra.DROUGHT and around.coastal:
            shift = round_half_up(shift / rules.climate_effects.coast_drought_divisor)
        if around.era is ClimateEra.RAIN and around.coastal:
            shift += rules.climate_effects.coast_rain_bonus
        value += shift
    return clamp_int(value, 0, PERCENT)


def band_of(rules: Rules, temperature: int) -> TemperatureBand:
    settings = rules.environment
    for band, ceiling in (
        (TemperatureBand.FROZEN, settings.frozen_below),
        (TemperatureBand.COLD, settings.cold_below),
        (TemperatureBand.TEMPERATE, settings.temperate_below),
        (TemperatureBand.WARM, settings.warm_below),
        (TemperatureBand.HOT, settings.hot_below),
    ):
        if temperature < ceiling:
            return band
    return TemperatureBand.SEARING


def seasonality_of(rules: Rules, latitude: int, axial_tilt: int) -> int:
    base = rules.seasons.seasonality_equator_pct
    return clamp_int(axial_tilt * PERCENT / rules.seasons.tilt_max * (base + latitude * (PERCENT - base) / PERCENT) / PERCENT, 0, PERCENT)


@dataclass(frozen=True)
class TerrainReading:
    geography: Geography
    around: Surroundings
    temperature: int
    rainfall: int
    wetland: int
    built: int


def _special_terrain(rules: Rules, reading: TerrainReading) -> TerrainKind | None:
    settings = rules.environment
    water = share(reading.geography.biome_mix, Biome.SHALLOW_WATER, Biome.DEEP_WATER)
    checks = (
        (water >= settings.sea_share_pct, TerrainKind.SEA),
        (reading.built >= settings.urban_built_pct, TerrainKind.URBAN),
        (reading.around.ruins >= settings.ruin_field_ruins, TerrainKind.RUIN_FIELD),
    )
    found = next((terrain for matched, terrain in checks if matched), None)
    return found or WORLD_TERRAIN.get(reading.around.world_type)


def _natural_terrain(rules: Rules, reading: TerrainReading) -> TerrainKind:
    settings = rules.environment
    dominant = settings.terrain_dominant_share_pct
    geography = reading.geography
    mix = geography.biome_mix
    warm = reading.temperature >= settings.warm_below
    rough = geography.roughness >= settings.canyon_roughness
    checks = (
        (reading.temperature < settings.frozen_below, TerrainKind.ICE_SHEET),
        (share(mix, Biome.SHALLOW_WATER, Biome.DEEP_WATER) >= settings.island_water_share_pct, TerrainKind.ISLAND),
        (share(mix, Biome.MOUNTAINS, Biome.PEAKS) >= dominant, TerrainKind.MOUNTAINS),
        (reading.wetland >= settings.marsh_wetland_pct, TerrainKind.MARSH),
        (share(mix, Biome.DRY_HILLS, Biome.WET_HILLS) >= dominant, TerrainKind.CANYON if rough else TerrainKind.HILLS),
        (reading.temperature < settings.cold_below, TerrainKind.TUNDRA),
        (
            share(mix, Biome.WET_LOWLAND) >= dominant or geography.base_forest >= settings.forest_terrain_pct,
            TerrainKind.JUNGLE if warm else TerrainKind.FOREST,
        ),
        (reading.rainfall < settings.desert_rainfall_below and reading.temperature >= settings.temperate_below, TerrainKind.DESERT),
        (geography.river_class is RiverClass.GREAT_RIVER, TerrainKind.RIVER_VALLEY),
        (share(mix, Biome.SHORE) >= dominant, TerrainKind.COAST),
        (share(mix, Biome.DRY_LOWLAND) >= dominant, TerrainKind.STEPPE),
    )
    return next((terrain for matched, terrain in checks if matched), TerrainKind.PLAIN)


def terrain_of(rules: Rules, reading: TerrainReading) -> TerrainKind:
    return _special_terrain(rules, reading) or _natural_terrain(rules, reading)


def soil_of(rules: Rules, geography: Geography, world_type: WorldType, wetland: int) -> SoilKind:
    settings = rules.environment
    special = WORLD_SOIL.get(world_type)
    if special is not None:
        return special
    mix = geography.biome_mix
    if wetland >= settings.peat_wetland_pct:
        return SoilKind.PEAT
    if share(mix, Biome.MOUNTAINS, Biome.PEAKS, Biome.DRY_HILLS) >= settings.terrain_dominant_share_pct:
        return SoilKind.THIN
    if share(mix, Biome.DRY_LOWLAND, Biome.SHORE) >= settings.terrain_dominant_share_pct:
        return SoilKind.SAND
    if share(mix, Biome.WET_LOWLAND) >= settings.terrain_dominant_share_pct:
        return SoilKind.CLAY
    return SoilKind.LOAM


def natural_soil(rules: Rules, soil: SoilKind, moisture: int) -> int:
    settings = rules.environment
    return clamp_int(SOIL_FERTILITY[soil](rules) + (moisture - settings.ideal_rainfall) * settings.soil_moisture_pct / PERCENT, 0, PERCENT)


def fit(value: int, ideal: int, tolerance: int, floor_pct: int) -> float:
    return max(floor_pct / PERCENT, 1 - abs(value - ideal) / max(1, tolerance))


def scar_penalty(rules: Rules, scars: Mapping[str, int]) -> float:
    kept = 1.0
    for key, depth in scars.items():
        kind = ScarKind(key)
        kept *= 1 - SCAR_FERTILITY[kind](rules) / PERCENT * min(depth, PERCENT) / PERCENT
    return 1 - kept


def climate_factor(rules: Rules, *, temperature: int, rainfall: int, river: RiverClass, scars: Mapping[str, int]) -> float:
    settings = rules.environment
    return (
        fit(rainfall, settings.ideal_rainfall, settings.rainfall_tolerance, settings.fit_floor_pct)
        * fit(temperature, settings.ideal_temperature, settings.temperature_tolerance, settings.fit_floor_pct)
        * (1 - scar_penalty(rules, scars))
        * (1 + RIVER_IRRIGATION[river](rules) / PERCENT)
    )


def fertility_from(soil_fertility: int, factor: float) -> int:
    return clamp_int(soil_fertility * factor, 0, PERCENT)


def soil_for(fertility: int, factor: float) -> int:
    return clamp_int(fertility / factor if factor > 0 else fertility, 0, PERCENT)


def disease_load_of(rules: Rules, *, temperature: int, wetland: int, built: int, density_pct: int, sanitation_pct: int, scars: Mapping[str, int]) -> int:
    settings = rules.environment
    warmth = temperature * settings.disease_warmth_pct / PERCENT
    wet = wetland * settings.disease_wetland_pct / PERCENT
    crowd = (density_pct + built) * settings.disease_density_pct / PERCENT
    plague = scars.get(ScarKind.PLAGUE_GROUND.value, 0) * rules.scars.plague_ground_disease_pct / PERCENT
    battle = scars.get(ScarKind.BATTLEFIELD.value, 0) * rules.scars.battlefield_disease_pct / PERCENT
    return clamp_int((warmth + wet + crowd + plague + battle) * (1 - sanitation_pct / PERCENT), 0, PERCENT)


COAST_BOATING: dict[CoastKind, Callable[[Rules], int]] = {
    CoastKind.NONE: lambda rules: 0,
    CoastKind.CLIFF: lambda rules: rules.passability.cliff_coast,
    CoastKind.BEACH: lambda rules: rules.passability.boat_coast,
    CoastKind.HARBOUR_SITE: lambda rules: rules.passability.harbour_coast,
    CoastKind.REEF: lambda rules: rules.passability.reef_coast,
}


def passability_of(
    rules: Rules, *, roughness: int, forest: int, wetland: int, river: RiverClass, temperature: int, coast: CoastKind, tides: int = 0
) -> dict[str, int]:
    settings = rules.passability
    cold = max(0, rules.weather.cold_threshold - temperature) * PERCENT // max(1, rules.weather.cold_threshold)
    river_pct = RIVER_RANK[river] * PERCENT // RIVER_TOP_RANK
    values: dict[str, int] = {}
    for mode, sensitivity in MODE_SENSITIVITY.items():
        weights = sensitivity(rules)
        loss = sum(weight * value / PERCENT for weight, value in zip(weights, (roughness, forest, wetland, river_pct, cold), strict=True))
        values[mode.value] = clamp_int(PERCENT - loss, settings.floor, PERCENT)
    tide = tides * settings.tide_boat_pct / PERCENT if coast is not CoastKind.NONE else 0
    values[MovementMode.BOAT.value] = clamp_int(river_pct * settings.boat_river_pct / PERCENT + COAST_BOATING[coast](rules) - tide, 0, PERCENT)
    values[MovementMode.FLYING.value] = clamp_int(PERCENT - roughness * settings.flying_roughness_pct / PERCENT, settings.floor, PERCENT)
    return values


def defensibility_of(rules: Rules, *, roughness: int, forest: int, river: RiverClass, chokepoints: int) -> int:
    settings = rules.environment
    return clamp_int(
        roughness * settings.defence_roughness_pct / PERCENT
        + forest * settings.defence_forest_pct / PERCENT
        + RIVER_RANK[river] * settings.defence_river_step
        + chokepoints * settings.defence_chokepoint_step,
        0,
        PERCENT,
    )


def mineral_layers(rules: Rules, rng: SeededRandom, geography: Geography, world_type: WorldType, terrain: TerrainKind) -> dict[str, int]:
    settings = rules.environment
    mix = geography.biome_mix
    mountains = share(mix, Biome.MOUNTAINS, Biome.PEAKS)
    hills = share(mix, Biome.DRY_HILLS, Biome.WET_HILLS)
    shore = share(mix, Biome.SHORE)
    lowland = share(mix, Biome.DRY_LOWLAND, Biome.MID_LOWLAND, Biome.WET_LOWLAND)
    candidates: dict[MaterialKind, int] = {
        MaterialKind.STONE: mountains + hills,
        MaterialKind.IRON: mountains + hills // 2,
        MaterialKind.COPPER: hills + mountains // 2,
        MaterialKind.TIN: mountains // 2,
        MaterialKind.LEAD: mountains // 2,
        MaterialKind.SILVER: mountains // 3,
        MaterialKind.GOLD: mountains // 4 + geography.roughness // 8,
        MaterialKind.GEMS: mountains // 5,
        MaterialKind.FLINT: hills // 2 + lowland // 4,
        MaterialKind.CLAY: lowland // 2 + geography.base_wetland // 2,
        MaterialKind.SALT: shore + (settings.desert_salt if terrain is TerrainKind.DESERT else 0),
        MaterialKind.AMBER: shore // 2 + geography.base_forest // 4,
    }
    if terrain is TerrainKind.VOLCANIC or world_type is WorldType.LAVA:
        candidates[MaterialKind.OBSIDIAN] = settings.volcanic_mineral
        candidates[MaterialKind.SULFUR] = settings.volcanic_mineral
    if world_type is WorldType.CRYSTAL or terrain is TerrainKind.CRYSTAL_FIELD:
        candidates[MaterialKind.CRYSTAL] = settings.crystal_mineral
    if world_type is WorldType.VOID_POCKET:
        candidates[MaterialKind.VOID_GLASS] = settings.void_mineral
    for material in WORLD_MINERALS.get(world_type, ()):
        candidates[material] = max(candidates.get(material, 0), settings.signature_mineral)
    layers: dict[str, int] = {}
    for material, presence in sorted(candidates.items(), key=lambda item: item[0].value):
        if presence < settings.mineral_presence_min:
            continue
        richness = clamp_int(presence * settings.mineral_richness_pct / PERCENT + rng.integer(-settings.mineral_spread, settings.mineral_spread), 0, PERCENT)
        if richness > 0:
            layers[material.value] = richness
    return layers
