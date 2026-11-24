from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.ecology import Biochemistry
from aerona.domain.enums.physics import AirNeed, LifeEnvironment

B = Biochemistry
UNBOUND = frozenset({B.VOID, B.SPIRIT})


@dataclass(frozen=True)
class AirSpec:
    label: str
    gas: str | None
    fits: frozenset[Biochemistry]


@dataclass(frozen=True)
class LifePlaceSpec:
    label: str
    gas_world: bool | None
    sea: bool = False
    land: bool = False
    frozen: bool = False
    buried: bool = False
    clouds: bool = False
    air: bool = False
    void: bool = False
    hot: bool = False


AIR_NEEDS: Mapping[AirNeed, AirSpec] = total(
    AirNeed,
    {
        AirNeed.OXYGEN: AirSpec("Oxygen", "oxygen", frozenset({B.CARBON_WATER, B.SILICON, B.CRYSTAL}) | UNBOUND),
        AirNeed.CARBON_DIOXIDE: AirSpec("Carbon dioxide", "carbon_dioxide", frozenset({B.CARBON_WATER, B.SILICON, B.CRYSTAL, B.CARBON_METHANE}) | UNBOUND),
        AirNeed.METHANE: AirSpec("Methane", "methane", frozenset({B.CARBON_METHANE, B.CARBON_AMMONIA}) | UNBOUND),
        AirNeed.AMMONIA: AirSpec("Ammonia", "ammonia", frozenset({B.CARBON_AMMONIA}) | UNBOUND),
        AirNeed.HYDROGEN: AirSpec("Hydrogen", "hydrogen", frozenset({B.CARBON_METHANE, B.CARBON_AMMONIA, B.PLASMA}) | UNBOUND),
        AirNeed.NONE: AirSpec("Breathes nothing", None, frozenset(Biochemistry)),
        AirNeed.SULPHUROUS: AirSpec("Sulphurous air", "sulphur_dioxide", frozenset({B.SILICON, B.CRYSTAL, B.PLASMA}) | UNBOUND),
    },
)

LIFE_PLACES: Mapping[LifeEnvironment, LifePlaceSpec] = total(
    LifeEnvironment,
    {
        LifeEnvironment.MARINE: LifePlaceSpec("Seas", False, sea=True),
        LifeEnvironment.TERRESTRIAL: LifePlaceSpec("Land", False, land=True),
        LifeEnvironment.AERIAL: LifePlaceSpec("Air", None, air=True),
        LifeEnvironment.SUBTERRANEAN: LifePlaceSpec("Beneath the ground", False, buried=True),
        LifeEnvironment.UNDER_ICE: LifePlaceSpec("Oceans under ice", False, sea=True, frozen=True),
        LifeEnvironment.CLOUD: LifePlaceSpec("Cloud layers", True, clouds=True),
        LifeEnvironment.VENT: LifePlaceSpec("Deep hot vents", False, sea=True, hot=True),
        LifeEnvironment.VOID: LifePlaceSpec("Between worlds", None, void=True),
    },
)


def air_fits(need: AirNeed, chemistry: Biochemistry) -> bool:
    return chemistry in AIR_NEEDS[need].fits


def first_fitting_air(chemistry: Biochemistry) -> AirNeed:
    return next(need for need, spec in AIR_NEEDS.items() if chemistry in spec.fits)
