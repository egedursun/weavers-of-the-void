from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from aerona.cartography.biomes import Biome
from aerona.catalog.climate import CLIMATES, climate_profile
from aerona.catalog.goods_tables import WORLD_MINERALS
from aerona.catalog.goods_traits import materials_with
from aerona.catalog.life.environment import WORLD_SOIL, WORLD_TEMPERATURE, WORLD_TERRAIN
from aerona.catalog.movement import MOVEMENT, MovementSpec
from aerona.catalog.scars import SCARS
from aerona.catalog.soils import SOILS
from aerona.catalog.terrain import TERRAIN, terrain_has
from aerona.catalog.wind_belts import CURRENTS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.environment import (
    CoastKind,
    MovementMedium,
    MovementWork,
    RiverClass,
    ScarKind,
    SoilKind,
    TemperatureBand,
    TerrainKind,
    TerrainTrait,
)
from aerona.domain.enums.goods_traits import MaterialTrait
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.world import ClimateEra, WorldType
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

RIVER_IRRIGATION: dict[RiverClass, Callable[[Rules], int]] = {
    RiverClass.NONE: lambda rules: 0,
    RiverClass.STREAM: lambda rules: rules.environment.stream_irrigation_pct,
    RiverClass.RIVER: lambda rules: rules.environment.river_irrigation_pct,
    RiverClass.GREAT_RIVER: lambda rules: rules.environment.great_river_irrigation_pct,
}

RIVER_RANK: dict[RiverClass, int] = {RiverClass.NONE: 0, RiverClass.STREAM: 1, RiverClass.RIVER: 2, RiverClass.GREAT_RIVER: 3}
RIVER_TOP_RANK = 3

COLD_INDEX = 4
MONTHS = 12
WARD_STEPS = 4


@dataclass(frozen=True)
class Works:
    roads: int = 0
    bridges: int = 0
    harbours: int = 0
    irrigation: int = 0
    waystations: int = 0
    wards: int = 0


@dataclass(frozen=True)
class Surroundings:
    world_type: WorldType
    era: ClimateEra | None
    coastal: bool
    highland: bool
    ruins: int = 0
    chokepoints: int = 0
    airless: bool = False
    gaseous: bool = False
    star_heat: int = 0
    works: Works = field(default_factory=Works)
    cleared: int = 0
    shift_heat: int = 0
    shift_rain: int = 0
    pass_shift: int = 0
    deltas: int = 0


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
    soil: SoilKind | None = None


def _special_terrain(rules: Rules, reading: TerrainReading) -> TerrainKind | None:
    settings = rules.environment
    water = share(reading.geography.biome_mix, Biome.SHALLOW_WATER, Biome.DEEP_WATER)
    checks = (
        (water >= settings.sea_share_pct, TerrainKind.SEA),
        (reading.built >= settings.urban_built_pct, TerrainKind.URBAN),
        (reading.around.ruins >= settings.ruin_field_ruins, TerrainKind.RUIN_FIELD),
    )
    found = next((terrain for matched, terrain in checks if matched), None)
    if found is None and reading.around.gaseous:
        return TerrainKind.CLOUD_DECK
    world_terrain = WORLD_TERRAIN.get(reading.around.world_type)
    if found is None and world_terrain is None and reading.around.airless:
        return TerrainKind.REGOLITH_PLAIN
    return found or world_terrain


def _natural_terrain(rules: Rules, reading: TerrainReading) -> TerrainKind:
    settings = rules.environment
    dominant = settings.terrain_dominant_share_pct
    geography = reading.geography
    mix = geography.biome_mix
    depth = rules.terrain_depth
    warm = reading.temperature >= settings.warm_below
    rough = geography.roughness >= settings.canyon_roughness
    hilly = share(mix, Biome.DRY_HILLS, Biome.WET_HILLS) >= dominant
    wooded = share(mix, Biome.WET_LOWLAND) >= dominant or geography.base_forest >= settings.forest_terrain_pct
    marshy = reading.wetland >= settings.marsh_wetland_pct
    shore = share(mix, Biome.SHORE) >= dominant or reading.around.coastal
    arid = reading.rainfall < settings.desert_rainfall_below
    dry_months = MONTHS * max(0, settings.ideal_rainfall - reading.rainfall) // max(1, settings.ideal_rainfall)
    checks = (
        (reading.temperature < settings.frozen_below, TerrainKind.ICE_SHEET),
        (share(mix, Biome.SHALLOW_WATER, Biome.DEEP_WATER) >= settings.island_water_share_pct, TerrainKind.ISLAND),
        (share(mix, Biome.MOUNTAINS, Biome.PEAKS) >= dominant, TerrainKind.MOUNTAINS),
        (marshy and shore and warm, TerrainKind.MANGROVE),
        (marshy and reading.temperature < settings.cold_below, TerrainKind.MOOR),
        (marshy, TerrainKind.MARSH),
        (hilly and rough and arid, TerrainKind.BADLANDS),
        (hilly and reading.soil is SoilKind.CALCAREOUS and reading.rainfall >= settings.ideal_rainfall, TerrainKind.KARST),
        (hilly, TerrainKind.CANYON if rough else TerrainKind.HILLS),
        (wooded and reading.temperature < rules.weather.cold_threshold + depth.taiga_cold_below, TerrainKind.TAIGA),
        (reading.temperature < settings.cold_below, TerrainKind.TUNDRA),
        (wooded, TerrainKind.JUNGLE if warm else TerrainKind.FOREST),
        (arid and reading.temperature >= settings.temperate_below and reading.soil is SoilKind.SALINE, TerrainKind.EVAPORITE_FLAT),
        (arid and reading.temperature >= settings.temperate_below, TerrainKind.DESERT),
        (geography.river_class is RiverClass.GREAT_RIVER, TerrainKind.RIVER_VALLEY),
        (geography.river_class is RiverClass.RIVER and share(mix, Biome.WET_LOWLAND) * 2 >= dominant, TerrainKind.FLOODPLAIN),
        (share(mix, Biome.SHORE) >= dominant, TerrainKind.COAST),
        (share(mix, Biome.DRY_LOWLAND) >= dominant and warm and dry_months >= depth.savanna_dry_months, TerrainKind.SAVANNA),
        (
            share(mix, Biome.DRY_LOWLAND) >= dominant and reading.rainfall < settings.ideal_rainfall and reading.temperature >= settings.temperate_below,
            TerrainKind.SCRUBLAND,
        ),
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
    dominant = settings.terrain_dominant_share_pct
    damp = geography.moisture < settings.ideal_rainfall and geography.latitude < settings.cold_latitude_pct // 2
    checks = (
        (wetland >= settings.peat_wetland_pct, SoilKind.PEAT),
        (wetland >= settings.peat_wetland_pct * 2 // 3, SoilKind.GLEY),
        (geography.river_class is RiverClass.GREAT_RIVER or (share(mix, Biome.SHORE) >= dominant and geography.river_class is RiverClass.RIVER), SoilKind.SILT),
        (geography.base_forest >= settings.forest_terrain_pct and geography.latitude >= settings.cold_latitude_pct, SoilKind.LEACHED),
        (share(mix, Biome.DRY_LOWLAND) >= dominant and settings.ideal_rainfall // 2 <= geography.moisture <= settings.ideal_rainfall, SoilKind.HUMIC),
        (share(mix, Biome.MOUNTAINS, Biome.PEAKS, Biome.DRY_HILLS) >= dominant, SoilKind.THIN),
        (share(mix, Biome.DRY_LOWLAND, Biome.SHORE) >= dominant, SoilKind.SAND),
        (share(mix, Biome.WET_LOWLAND) >= dominant, SoilKind.CRACKING_CLAY if damp else SoilKind.CLAY),
    )
    return next((soil for matched, soil in checks if matched), SoilKind.LOAM)


def natural_soil(rules: Rules, soil: SoilKind, moisture: int) -> int:
    settings = rules.environment
    return clamp_int(SOILS[soil].fertility(rules) + (moisture - settings.ideal_rainfall) * settings.soil_moisture_pct / PERCENT, 0, PERCENT)


def fit(value: int, ideal: int, tolerance: int, floor_pct: int) -> float:
    return max(floor_pct / PERCENT, 1 - abs(value - ideal) / max(1, tolerance))


def scar_penalty(rules: Rules, scars: Mapping[str, int]) -> float:
    kept = 1.0
    for key, depth in scars.items():
        kind = ScarKind(key)
        kept *= 1 - SCARS[kind].fertility(rules) / PERCENT * min(depth, PERCENT) / PERCENT
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


def climate_disease(rules: Rules, *, temperature: int, wetland: int) -> float:
    settings = rules.environment
    return max(0.0, temperature * settings.disease_warmth_pct / PERCENT + wetland * settings.disease_wetland_pct / PERCENT)


def disease_load_of(rules: Rules, *, temperature: int, wetland: int, built: int, density_pct: int, sanitation_pct: int, scars: Mapping[str, int]) -> int:
    settings = rules.environment
    native = climate_disease(rules, temperature=temperature, wetland=wetland)
    crowd = (density_pct + built) * settings.disease_density_pct / PERCENT
    plague = scars.get(ScarKind.PLAGUE_GROUND.value, 0) * rules.scars.plague_ground_disease_pct / PERCENT
    battle = scars.get(ScarKind.BATTLEFIELD.value, 0) * rules.scars.battlefield_disease_pct / PERCENT
    return clamp_int((native + crowd + plague + battle) * (1 - sanitation_pct / PERCENT), 0, PERCENT)


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
    sacred: int = 0
    scars: Mapping[str, int] = field(default_factory=dict)
    deltas: int = 0
    current: OceanCurrent = OceanCurrent.NONE


def water_passage(rules: Rules, ground: Ground, river_pct: int, spec: MovementSpec) -> float:
    settings = rules.passability
    tide = ground.tides * settings.tide_boat_pct / PERCENT if ground.coast is not CoastKind.NONE else 0
    shored = ground.coast is not CoastKind.NONE or ground.river is not RiverClass.NONE
    harbours = ground.works.harbours * settings.harbour_works_pct if shored and spec.takes(MovementWork.HARBOURS) else 0
    return river_pct * settings.boat_river_pct / PERCENT + COAST_BOATING[ground.coast](rules) - tide + harbours + ground.deltas * rules.places.delta_harbour


def afloat(rules: Rules, ground: Ground, river_pct: int, spec: MovementSpec, terrain_pct: int) -> float:
    water = water_passage(rules, ground, river_pct, spec)
    return max(water, terrain_pct) if terrain_has(ground.terrain, TerrainTrait.WATERY) else water


def passability_of(rules: Rules, ground: Ground) -> dict[str, int]:
    settings = rules.passability
    works = ground.works
    cold = max(0, rules.weather.cold_threshold - ground.temperature) * PERCENT // max(1, rules.weather.cold_threshold)
    bridged = max(0.0, 1 - works.bridges * settings.bridge_crossing_pct / PERCENT)
    river_pct = RIVER_RANK[ground.river] * PERCENT // RIVER_TOP_RANK
    passage = TERRAIN[ground.terrain].passage(rules)
    scarred = scar_passage(rules, ground.scars)
    values: dict[str, int] = {}
    for mode, spec in MOVEMENT.items():
        share = passage[mode] / PERCENT
        if spec.medium is MovementMedium.WATER_SURFACE:
            chilled = PERCENT - cold * spec.sensitivity(rules)[COLD_INDEX] // PERCENT
            values[mode.value] = clamp_int(afloat(rules, ground, river_pct, spec, passage[mode]) * share * chilled / PERCENT, 0, PERCENT)
            continue
        if spec.medium is MovementMedium.UNDER_WATER:
            iced = PERCENT - cold * settings.submerged_ice_cut_pct // PERCENT
            beneath = afloat(rules, ground, river_pct, spec, passage[mode]) * share * iced / PERCENT
            drift = CURRENTS[ground.current].sailing_pct(rules) * settings.submerged_current_pct / PERCENT if beneath > 0 else 0
            values[mode.value] = clamp_int(beneath + drift, 0, PERCENT)
            continue
        if spec.medium is MovementMedium.THROUGH_MATTER and not any(spec.sensitivity(rules)):
            warded = min(
                PERCENT, works.wards * settings.incorporeal_ward_cut_pct // WARD_STEPS + ground.sacred * settings.incorporeal_sacred_cut_pct // PERCENT
            )
            values[mode.value] = clamp_int(passage[mode] * (PERCENT - warded) / PERCENT, 0, PERCENT)
            continue
        crossing = bridged if spec.takes(MovementWork.BRIDGES) else 1.0
        features = (ground.roughness, ground.forest, ground.wetland, river_pct * crossing, cold)
        loss = sum(weight * value / PERCENT for weight, value in zip(spec.sensitivity(rules), features, strict=True))
        roads = min(settings.road_cap_pct, works.roads * settings.road_step_pct) if spec.takes(MovementWork.ROADS) and share > 0 else 0
        values[mode.value] = clamp_int(((PERCENT - loss) * share + roads) * (PERCENT - scarred) / PERCENT, settings.floor if share > 0 else 0, PERCENT)
    return values


def scar_passage(rules: Rules, scars: Mapping[str, int]) -> int:
    return clamp_int(round_half_up(sum(depth * SCARS[ScarKind(key)].passage(rules) / PERCENT for key, depth in sorted(scars.items()))), 0, PERCENT)


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
    flats = rules.terrain_depth.evaporite_flat_yield if terrain is TerrainKind.EVAPORITE_FLAT else 0
    candidates[MaterialKind.HALITE] = shore + (settings.desert_halite if terrain is TerrainKind.DESERT else 0) + flats
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
