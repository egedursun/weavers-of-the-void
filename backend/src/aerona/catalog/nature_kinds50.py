from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body_systems import BodySystem, Sensitivity
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import SoilKind
from aerona.domain.enums.fossil import Preservation
from aerona.domain.enums.geology import RockKind
from aerona.domain.enums.plants import PlantReproduction
from aerona.domain.enums.space_weather import SpaceWeatherKind
from aerona.domain.enums.water import CoastForm, LocalClimateCause, SedimentCarrier, SedimentKind
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class SystemSpec:
    label: str
    worn: bool


@dataclass(frozen=True)
class SensitivitySpec:
    label: str
    by_goods: bool


@dataclass(frozen=True)
class PreservationSpec:
    label: str
    keeps_soft: bool
    fuel: CommodityKind | None


@dataclass(frozen=True)
class SpaceWeatherSpec:
    label: str
    from_star: bool


@dataclass(frozen=True)
class CoastSpec:
    label: str
    build: Callable[[Rules], int]
    wear: Callable[[Rules], int]
    silting_pct: int


@dataclass(frozen=True)
class LocalCauseSpec:
    label: str
    heat: int
    humidity: int


@dataclass(frozen=True)
class CarrierSpec:
    label: str
    kind: SedimentKind


@dataclass(frozen=True)
class SedimentSpec:
    label: str
    fertility: Callable[[Rules], int]
    fill: Callable[[Rules], int]
    carriers: frozenset[SedimentCarrier]
    soil: SoilKind
    rock: RockKind


@dataclass(frozen=True)
class ReproductionSpec:
    label: str
    by_wind: bool
    by_beasts: bool


B = BodySystem
BODY_SYSTEMS: MappingProxyType[BodySystem, SystemSpec] = total(
    B,
    {
        B.BREATH: SystemSpec("Breath", True),
        B.CIRCULATION: SystemSpec("Circulation", False),
        B.DIGESTION: SystemSpec("Digestion", False),
        B.REGULATION: SystemSpec("Regulation", True),
        B.NERVES: SystemSpec("Nerves", False),
        B.IMMUNITY: SystemSpec("Immunity", False),
        B.REPRODUCTION: SystemSpec("Reproduction", False),
        B.STRUCTURE: SystemSpec("Structure", True),
        B.NONE: SystemSpec("No system", False),
    },
)

S = Sensitivity
SENSITIVITIES: MappingProxyType[Sensitivity, SensitivitySpec] = total(
    S,
    {
        S.TO_FOOD: SensitivitySpec("To a food", True),
        S.TO_PLANT: SensitivitySpec("To a plant", True),
        S.TO_ANIMAL: SensitivitySpec("To an animal", True),
        S.TO_MATERIAL: SensitivitySpec("To a material", True),
        S.TO_SUBSTANCE: SensitivitySpec("To a substance", True),
        S.TO_LIGHT: SensitivitySpec("To light", False),
        S.TO_SOUND: SensitivitySpec("To sound", False),
        S.TO_POWER: SensitivitySpec("To a power", False),
    },
)

P = Preservation
PRESERVATIONS: MappingProxyType[Preservation, PreservationSpec] = total(
    P,
    {
        P.ROCK: PreservationSpec("Rock", False, None),
        P.AMBER: PreservationSpec("Amber", True, None),
        P.ICE: PreservationSpec("Ice", True, None),
        P.BOG: PreservationSpec("Bog", True, CommodityKind.PEAT),
        P.TAR: PreservationSpec("Tar", False, CommodityKind.COAL),
        P.ASH: PreservationSpec("Ash", False, None),
        P.DRY: PreservationSpec("Dry ground", False, None),
    },
)

W = SpaceWeatherKind
SPACE_WEATHER: MappingProxyType[SpaceWeatherKind, SpaceWeatherSpec] = total(
    W,
    {
        W.FLARE: SpaceWeatherSpec("Flare", True),
        W.PARTICLE_STORM: SpaceWeatherSpec("Particle storm", True),
        W.FIELD_STORM: SpaceWeatherSpec("Field storm", True),
        W.FIELD_REVERSAL: SpaceWeatherSpec("Field reversal", False),
        W.COSMIC_RAY_BURST: SpaceWeatherSpec("Burst of rays", False),
        W.WIND_SURGE: SpaceWeatherSpec("Wind surge", True),
    },
)

C = CoastForm
COAST_FORMS: MappingProxyType[CoastForm, CoastSpec] = total(
    C,
    {
        C.CLIFF: CoastSpec("Cliff", lambda rules: rules.coasts.cliff_build_rate, lambda rules: rules.coasts.cliff_wear_rate, 50),
        C.BEACH: CoastSpec("Beach", lambda rules: rules.coasts.beach_build_rate, lambda rules: rules.coasts.beach_wear_rate, 100),
        C.DELTA: CoastSpec("Delta", lambda rules: rules.coasts.delta_build_rate, lambda rules: rules.coasts.delta_wear_rate, 150),
        C.MARSH: CoastSpec("Marsh", lambda rules: rules.coasts.marsh_build_rate, lambda rules: rules.coasts.marsh_wear_rate, 150),
        C.REEF: CoastSpec("Reef", lambda rules: rules.coasts.reef_build_rate, lambda rules: rules.coasts.reef_wear_rate, 80),
        C.ICE_SHELF: CoastSpec("Ice shelf", lambda rules: rules.coasts.ice_shelf_build_rate, lambda rules: rules.coasts.ice_shelf_wear_rate, 30),
        C.FJORD: CoastSpec("Fjord", lambda rules: rules.coasts.fjord_build_rate, lambda rules: rules.coasts.fjord_wear_rate, 30),
        C.LAGOON: CoastSpec("Lagoon", lambda rules: rules.coasts.lagoon_build_rate, lambda rules: rules.coasts.lagoon_wear_rate, 200),
        C.ESTUARY: CoastSpec("Estuary", lambda rules: rules.coasts.estuary_build_rate, lambda rules: rules.coasts.estuary_wear_rate, 160),
        C.MANGROVE: CoastSpec("Mangrove", lambda rules: rules.coasts.mangrove_build_rate, lambda rules: rules.coasts.mangrove_wear_rate, 120),
        C.BARRIER_ISLAND: CoastSpec(
            "Barrier island", lambda rules: rules.coasts.barrier_island_build_rate, lambda rules: rules.coasts.barrier_island_wear_rate, 60
        ),
    },
)

L = LocalClimateCause
LOCAL_CAUSES: MappingProxyType[LocalClimateCause, LocalCauseSpec] = total(
    L,
    {
        L.VALLEY: LocalCauseSpec("Valley", -2, 5),
        L.SLOPE: LocalCauseSpec("Slope", -3, -3),
        L.WATER: LocalCauseSpec("Water", -1, 8),
        L.FOREST: LocalCauseSpec("Forest", -2, 6),
        L.BUILT: LocalCauseSpec("Built land", 0, 0),
    },
)

K = SedimentKind
SEDIMENTS: MappingProxyType[SedimentKind, SedimentSpec] = total(
    K,
    {
        K.SILT: SedimentSpec(
            "Silt",
            lambda rules: rules.sediment.silt_fertility,
            lambda rules: rules.sediment.silt_fill,
            frozenset({SedimentCarrier.RIVER, SedimentCarrier.WIND}),
            SoilKind.SILT,
            RockKind.SHALE,
        ),
        K.SAND: SedimentSpec(
            "Sand",
            lambda rules: rules.sediment.sand_fertility,
            lambda rules: rules.sediment.sand_fill,
            frozenset({SedimentCarrier.WIND, SedimentCarrier.WAVE, SedimentCarrier.RIVER}),
            SoilKind.SAND,
            RockKind.SANDSTONE,
        ),
        K.GRAVEL: SedimentSpec(
            "Gravel",
            lambda rules: rules.sediment.gravel_fertility,
            lambda rules: rules.sediment.gravel_fill,
            frozenset({SedimentCarrier.ICE, SedimentCarrier.SLOPE, SedimentCarrier.RIVER}),
            SoilKind.THIN,
            RockKind.SANDSTONE,
        ),
        K.VOLCANIC: SedimentSpec(
            "Volcanic ash",
            lambda rules: rules.sediment.volcanic_fertility,
            lambda rules: rules.sediment.volcanic_fill,
            frozenset({SedimentCarrier.WIND, SedimentCarrier.SLOPE}),
            SoilKind.TEPHRA,
            RockKind.TUFF,
        ),
        K.ORGANIC: SedimentSpec(
            "Organic matter",
            lambda rules: rules.sediment.organic_fertility,
            lambda rules: rules.sediment.organic_fill,
            frozenset({SedimentCarrier.RIVER, SedimentCarrier.WAVE}),
            SoilKind.PEAT,
            RockKind.COAL,
        ),
        K.CLAY: SedimentSpec(
            "Clay",
            lambda rules: rules.sediment.clay_fertility,
            lambda rules: rules.sediment.clay_fill,
            frozenset({SedimentCarrier.RIVER, SedimentCarrier.WAVE}),
            SoilKind.CLAY,
            RockKind.SHALE,
        ),
        K.CARBONATE: SedimentSpec(
            "Carbonate",
            lambda rules: rules.sediment.carbonate_fertility,
            lambda rules: rules.sediment.carbonate_fill,
            frozenset({SedimentCarrier.WAVE}),
            SoilKind.CALCAREOUS,
            RockKind.LIMESTONE,
        ),
        K.EVAPORITE: SedimentSpec(
            "Evaporite",
            lambda rules: rules.sediment.evaporite_fertility,
            lambda rules: rules.sediment.evaporite_fill,
            frozenset({SedimentCarrier.RIVER, SedimentCarrier.WIND}),
            SoilKind.SALINE,
            RockKind.HALITE,
        ),
    },
)

R = SedimentCarrier
CARRIERS: MappingProxyType[SedimentCarrier, CarrierSpec] = total(
    R,
    {
        R.RIVER: CarrierSpec("River", K.SILT),
        R.WIND: CarrierSpec("Wind", K.SAND),
        R.ICE: CarrierSpec("Ice", K.GRAVEL),
        R.WAVE: CarrierSpec("Wave", K.SAND),
        R.SLOPE: CarrierSpec("Slope", K.GRAVEL),
    },
)

D = PlantReproduction
REPRODUCTIONS: MappingProxyType[PlantReproduction, ReproductionSpec] = total(
    D,
    {
        D.WIND_SEED: ReproductionSpec("Seeds on the wind", True, False),
        D.ANIMAL_SEED: ReproductionSpec("Seeds carried by beasts", False, True),
        D.SPORE: ReproductionSpec("Spores", True, False),
        D.RUNNER: ReproductionSpec("Runners", False, False),
        D.CUTTING: ReproductionSpec("Cuttings", False, False),
        D.MADE: ReproductionSpec("Made", False, False),
    },
)
