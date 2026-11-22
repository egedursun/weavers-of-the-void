from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from aerona.cartography.biomes import Biome
from aerona.catalog.climate import CLIMATES, climate_profile
from aerona.catalog.goods_tables import WORLD_MINERALS
from aerona.catalog.goods_traits import materials_with
from aerona.catalog.life.environment import WORLD_SOIL, WORLD_TEMPERATURE, WORLD_TERRAIN
from aerona.catalog.movement import MOVEMENT, MovementSpec
from aerona.catalog.terrain import TERRAIN
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.core.total import total
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.domain.enums.environment import (
    CoastKind,
    MovementMedium,
    MovementWork,
    RiverClass,
    ScarKind,
    SoilKind,
    TemperatureBand,
    TerrainKind,
)
from aerona.domain.enums.goods_traits import MaterialTrait
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.world import ClimateEra, WorldType
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

SOIL_FERTILITY: Mapping[SoilKind, Callable[[Rules], int]] = total(
    SoilKind,
    {
        SoilKind.THIN: lambda rules: rules.environment.soil_thin,
        SoilKind.LOAM: lambda rules: rules.environment.soil_loam,
        SoilKind.CLAY: lambda rules: rules.environment.soil_clay,
        SoilKind.SAND: lambda rules: rules.environment.soil_sand,
        SoilKind.VOLCANIC: lambda rules: rules.environment.soil_volcanic,
        SoilKind.PEAT: lambda rules: rules.environment.soil_peat,
        SoilKind.SALINE: lambda rules: rules.environment.soil_salt,
        SoilKind.TEPHRA: lambda rules: rules.environment.soil_ash,
        SoilKind.CRYSTALLINE: lambda rules: rules.environment.soil_crystal,
        SoilKind.CALCAREOUS: lambda rules: rules.environment.soil_bone,
        SoilKind.LATERITE: lambda rules: rules.environment.soil_laterite,
        SoilKind.PERMAFROST: lambda rules: rules.environment.soil_permafrost,
        SoilKind.REGOLITH: lambda rules: rules.environment.soil_regolith,
        SoilKind.ARTIFICIAL: lambda rules: rules.environment.soil_artificial,
    },
)

SCAR_FERTILITY: Mapping[ScarKind, Callable[[Rules], int]] = total(
    ScarKind,
    {
        ScarKind.BATTLEFIELD: lambda rules: rules.scars.battlefield_fertility_pct,
        ScarKind.PLAGUE_GROUND: lambda rules: rules.scars.plague_ground_fertility_pct,
        ScarKind.MADE_BARREN: lambda rules: rules.scars.salted_earth_fertility_pct,
        ScarKind.BURNED: lambda rules: rules.scars.burned_fertility_pct,
        ScarKind.CRATER: lambda rules: rules.scars.crater_fertility_pct,
        ScarKind.HAUNTED: lambda rules: rules.scars.haunted_fertility_pct,
        ScarKind.BLIGHTED: lambda rules: rules.scars.blighted_fertility_pct,
        ScarKind.LEAK_WOUND: lambda rules: rules.scars.leak_wound_fertility_pct,
        ScarKind.PLUNDERED: lambda rules: rules.campaign_depth.plunder_harvest_pct,
        ScarKind.EARTHWORKS: lambda rules: rules.army_depth.earthworks_fertility_pct,
        ScarKind.MILITARY_ROAD: lambda rules: rules.army_depth.road_fertility_pct,
        ScarKind.BRIDGE_DOWN: lambda rules: rules.army_depth.bridge_down_fertility_pct,
    },
)
RIVER_IRRIGATION: dict[RiverClass, Callable[[Rules], int]] = {
    RiverClass.NONE: lambda rules: 0,
    RiverClass.STREAM: lambda rules: rules.environment.stream_irrigation_pct,
    RiverClass.RIVER: lambda rules: rules.environment.river_irrigation_pct,
    RiverClass.GREAT_RIVER: lambda rules: rules.environment.great_river_irrigation_pct,
}

RIVER_RANK: dict[RiverClass, int] = {RiverClass.NONE: 0, RiverClass.STREAM: 1, RiverClass.RIVER: 2, RiverClass.GREAT_RIVER: 3}
RIVER_TOP_RANK = 3


@dataclass(frozen=True)
class Works:
    roads: int = 0
    bridges: int = 0
    harbours: int = 0
    irrigation: int = 0
    waystations: int = 0


@dataclass(frozen=True)
class Surroundings:
    world_type: WorldType
    era: ClimateEra | None
    coastal: bool
    highland: bool
    ruins: int = 0
    chokepoints: int = 0
    star_heat: int = 0
    works: Works = field(default_factory=Works)
    cleared: int = 0
    shift_heat: int = 0
    shift_rain: int = 0
    pass_shift: int = 0


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


TERMINATOR = PERCENT // 2


def band_heat(rules: Rules, geography: Geography, world_type: WorldType) -> float:
    settings = rules.environment
    if world_type is not WorldType.TIDALLY_LOCKED:
        return -geography.latitude * settings.latitude_cooling_pct / PERCENT
    if geography.latitude <= TERMINATOR:
        return (TERMINATOR - geography.latitude) / TERMINATOR * settings.locked_day_heat
    return -(geography.latitude - TERMINATOR) / TERMINATOR * settings.locked_night_cold


def temperature_of(rules: Rules, geography: Geography, around: Surroundings) -> int:
    settings = rules.environment
    value = (
        WORLD_TEMPERATURE[around.world_type](rules)
        + around.star_heat
        + band_heat(rules, geography, around.world_type)
        - geography.elevation_mean * settings.elevation_cooling_pct / PERCENT
        + around.shift_heat
    )
    if around.coastal:
        value += (settings.coast_moderation_target - value) * settings.coast_moderation_pct / PERCENT
    if around.era is not None:
        value += climate_profile(rules, around.era).temperature_shift
        if around.highland:
            value -= CLIMATES[around.era].highland_cooling(rules)
    return clamp_int(value, 0, PERCENT)


def rainfall_of(rules: Rules, geography: Geography, around: Surroundings) -> int:
    settings = rules.environment
    value = geography.moisture * settings.rain_from_moisture_pct / PERCENT + (settings.coastal_rainfall if around.coastal else 0)
    value -= geography.base_forest * around.cleared / PERCENT * settings.forest_rain_pct / PERCENT
    value += around.shift_rain
    if around.era is not None:
        shift = climate_profile(rules, around.era).rain_shift
        if around.coastal:
            spec = CLIMATES[around.era]
            shift = round_half_up(shift / spec.coast_rain_divisor(rules)) + spec.coast_rain_bonus(rules)
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


def irrigation_pct(rules: Rules, river: RiverClass, works: Works) -> int:
    settings = rules.environment
    dug = min(settings.irrigation_works_cap_pct, works.irrigation * settings.irrigation_works_pct) if river is not RiverClass.NONE else 0
    return RIVER_IRRIGATION[river](rules) + dug


@dataclass(frozen=True)
class CropMix:
    grain: float
    pasture: float
    fish: float


def crop_mix(rules: Rules, *, farmed: int, grazed: int, coastal: bool, river: RiverClass, sea: int | None = None) -> CropMix:
    settings = rules.environment
    coast = settings.coast_fishing_share if sea is None else sea
    water = coast if coastal else settings.river_fishing_share if river is not RiverClass.NONE else 0
    land = max(0.0, 1 - water / PERCENT)
    sown = farmed + grazed
    grain = farmed / sown if sown > 0 else 1.0
    return CropMix(grain=land * grain, pasture=land * (1 - grain), fish=water / PERCENT)


def rain_fit(rules: Rules, rainfall: int, mix: CropMix) -> float:
    settings = rules.environment
    grain = fit(rainfall, settings.ideal_rainfall, settings.rainfall_tolerance, settings.fit_floor_pct)
    pasture = fit(rainfall, settings.pasture_ideal_rainfall, settings.pasture_rainfall_tolerance, settings.fit_floor_pct)
    return mix.grain * grain + mix.pasture * pasture + mix.fish


def climate_factor(
    rules: Rules, *, temperature: int, rainfall: int, river: RiverClass, scars: Mapping[str, int], works: Works, mix: CropMix | None = None
) -> float:
    settings = rules.environment
    crops = mix if mix is not None else CropMix(1.0, 0.0, 0.0)
    return (
        rain_fit(rules, rainfall, crops)
        * fit(temperature, settings.ideal_temperature, settings.temperature_tolerance, settings.fit_floor_pct)
        * (1 - scar_penalty(rules, scars))
        * (1 + irrigation_pct(rules, river, works) / PERCENT)
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


@dataclass(frozen=True)
class Ground:
    roughness: int
    forest: int
    wetland: int
    river: RiverClass
    temperature: int
    coast: CoastKind
    terrain: TerrainKind
    tides: int = 0
    works: Works = field(default_factory=Works)


def water_passage(rules: Rules, ground: Ground, river_pct: int, spec: MovementSpec) -> float:
    settings = rules.passability
    tide = ground.tides * settings.tide_boat_pct / PERCENT if ground.coast is not CoastKind.NONE else 0
    shored = ground.coast is not CoastKind.NONE or ground.river is not RiverClass.NONE
    harbours = ground.works.harbours * settings.harbour_works_pct if shored and spec.takes(MovementWork.HARBOURS) else 0
    return river_pct * settings.boat_river_pct / PERCENT + COAST_BOATING[ground.coast](rules) - tide + harbours


def passability_of(rules: Rules, ground: Ground) -> dict[str, int]:
    settings = rules.passability
    works = ground.works
    cold = max(0, rules.weather.cold_threshold - ground.temperature) * PERCENT // max(1, rules.weather.cold_threshold)
    bridged = max(0.0, 1 - works.bridges * settings.bridge_crossing_pct / PERCENT)
    river_pct = RIVER_RANK[ground.river] * PERCENT // RIVER_TOP_RANK
    passage = TERRAIN[ground.terrain].passage(rules)
    values: dict[str, int] = {}
    for mode, spec in MOVEMENT.items():
        share = passage[mode] / PERCENT
        if spec.medium is MovementMedium.WATER_SURFACE:
            values[mode.value] = clamp_int(water_passage(rules, ground, river_pct, spec) * share, 0, PERCENT)
            continue
        crossing = bridged if spec.takes(MovementWork.BRIDGES) else 1.0
        features = (ground.roughness, ground.forest, ground.wetland, river_pct * crossing, cold)
        loss = sum(weight * value / PERCENT for weight, value in zip(spec.sensitivity(rules), features, strict=True))
        roads = min(settings.road_cap_pct, works.roads * settings.road_step_pct) if spec.takes(MovementWork.ROADS) else 0
        values[mode.value] = clamp_int((PERCENT - loss) * share + roads, settings.floor, PERCENT)
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


@dataclass(frozen=True)
class Make:
    metal: float = 1.0
    stone: float = 1.0
    rare: float = 1.0


def make_of(rules: Rules, physics: WorldPhysicsRow | None) -> Make:
    if physics is None:
        return Make()
    table = rules.orbits
    return Make(
        metal=physics.iron / max(1, table.iron_reference),
        stone=physics.rock / max(1, table.rock_reference),
        rare=1 + physics.exotic / max(1, table.exotic_reference),
    )


METAL_SEAMS = frozenset(materials_with(MaterialTrait.METAL_SEAM))
STONE_SEAMS = frozenset(materials_with(MaterialTrait.STONE_SEAM))
RARE_SEAMS = frozenset(materials_with(MaterialTrait.RARE_SEAM))


def make_factor(make: Make, material: MaterialKind) -> float:
    if material in METAL_SEAMS:
        return make.metal
    if material in STONE_SEAMS:
        return make.stone
    return make.rare if material in RARE_SEAMS else 1.0


def mineral_layers(
    rules: Rules, rng: SeededRandom, geography: Geography, world_type: WorldType, terrain: TerrainKind, *, make: Make | None = None
) -> dict[str, int]:
    settings = rules.environment
    mix = geography.biome_mix
    mountains = share(mix, Biome.MOUNTAINS, Biome.PEAKS)
    hills = share(mix, Biome.DRY_HILLS, Biome.WET_HILLS)
    shore = share(mix, Biome.SHORE)
    lowland = share(mix, Biome.DRY_LOWLAND, Biome.MID_LOWLAND, Biome.WET_LOWLAND)
    candidates: dict[MaterialKind, int] = {}
    candidates[MaterialKind.STONE] = mountains + hills
    candidates[MaterialKind.IRON] = mountains + hills // 2
    candidates[MaterialKind.COPPER] = hills + mountains // 2
    candidates[MaterialKind.TIN] = mountains // 2
    candidates[MaterialKind.LEAD] = mountains // 2
    candidates[MaterialKind.SILVER] = mountains // 3
    candidates[MaterialKind.GOLD] = mountains // 4 + geography.roughness // 8
    candidates[MaterialKind.GEMS] = mountains // 5
    candidates[MaterialKind.FLINT] = hills // 2 + lowland // 4
    candidates[MaterialKind.CLAY] = lowland // 2 + geography.base_wetland // 2
    candidates[MaterialKind.HALITE] = shore + (settings.desert_halite if terrain is TerrainKind.DESERT else 0)
    candidates[MaterialKind.AMBER] = shore // 2 + geography.base_forest // 4
    if terrain is TerrainKind.VOLCANIC or world_type is WorldType.LAVA:
        candidates[MaterialKind.OBSIDIAN] = settings.volcanic_mineral
        candidates[MaterialKind.SULFUR] = settings.volcanic_mineral
    if world_type is WorldType.CRYSTAL or terrain is TerrainKind.CRYSTAL_FIELD:
        candidates[MaterialKind.CRYSTAL] = settings.crystal_mineral
    if world_type is WorldType.VOID_POCKET:
        candidates[MaterialKind.VOID_GLASS] = settings.void_mineral
    for material in WORLD_MINERALS.get(world_type, ()):
        candidates[material] = max(candidates.get(material, 0), settings.signature_mineral)
    body = make or Make()
    for material, presence in list(candidates.items()):
        candidates[material] = round_half_up(presence * make_factor(body, material))
    layers: dict[str, int] = {}
    for material, presence in sorted(candidates.items(), key=lambda item: item[0].value):
        if presence < settings.mineral_presence_min:
            continue
        richness = clamp_int(presence * settings.mineral_richness_pct / PERCENT + rng.integer(-settings.mineral_spread, settings.mineral_spread), 0, PERCENT)
        if richness > 0:
            layers[material.value] = richness
    return layers
