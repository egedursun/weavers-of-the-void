from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body_systems import BodySystem, Sensitivity
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.fossil import Preservation
from aerona.domain.enums.plants import PlantReproduction
from aerona.domain.enums.space_weather import SpaceWeatherKind
from aerona.domain.enums.water import CoastForm, LocalClimateCause, SedimentCarrier, SedimentKind


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
    wear_pct: int
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
    fertility_pct: int


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
        C.CLIFF: CoastSpec("Cliff", 50, 50),
        C.BEACH: CoastSpec("Beach", 150, 100),
        C.DELTA: CoastSpec("Delta", 100, 150),
        C.MARSH: CoastSpec("Marsh", 80, 150),
        C.REEF: CoastSpec("Reef", 30, 80),
        C.ICE_SHELF: CoastSpec("Ice shelf", 200, 30),
        C.FJORD: CoastSpec("Fjord", 40, 30),
        C.LAGOON: CoastSpec("Lagoon", 60, 200),
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
        K.SILT: SedimentSpec("Silt", 150),
        K.SAND: SedimentSpec("Sand", 50),
        K.GRAVEL: SedimentSpec("Gravel", 30),
        K.VOLCANIC: SedimentSpec("Volcanic ash", 200),
        K.ORGANIC: SedimentSpec("Organic matter", 180),
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
