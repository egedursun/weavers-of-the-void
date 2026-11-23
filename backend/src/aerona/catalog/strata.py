from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.cosmography import DimensionKind
from aerona.domain.enums.faith import StratumActivity, StratumAdmission, StratumContact, StratumKind, StratumPermanence, StratumValence
from aerona.domain.enums.geology import UndergroundStratum


@dataclass(frozen=True)
class StratumAxes:
    valence: StratumValence
    permanence: StratumPermanence
    admission: StratumAdmission
    activity: StratumActivity
    contact: StratumContact


STRATUM_AXES: Mapping[StratumKind, StratumAxes] = total(
    StratumKind,
    {
        StratumKind.REWARD: StratumAxes(
            StratumValence.REWARD, StratumPermanence.ETERNAL, StratumAdmission.BY_DEEDS, StratumActivity.REST, StratumContact.BY_RITE
        ),
        StratumKind.COMMON: StratumAxes(StratumValence.NEUTRAL, StratumPermanence.ETERNAL, StratumAdmission.ALL, StratumActivity.REST, StratumContact.OPEN),
        StratumKind.PUNISHMENT: StratumAxes(
            StratumValence.PUNISHMENT, StratumPermanence.UNTIL_JUDGEMENT, StratumAdmission.BY_DEEDS, StratumActivity.STRUGGLE, StratumContact.CLOSED
        ),
        StratumKind.DISSOLUTION: StratumAxes(
            StratumValence.NEUTRAL, StratumPermanence.FADING, StratumAdmission.ALL, StratumActivity.DISSOLUTION, StratumContact.CLOSED
        ),
        StratumKind.BY_MANNER_OF_DEATH: StratumAxes(
            StratumValence.REWARD, StratumPermanence.ETERNAL, StratumAdmission.BY_MANNER_OF_DEATH, StratumActivity.STRUGGLE, StratumContact.BY_RITE
        ),
        StratumKind.BY_LINE: StratumAxes(
            StratumValence.REWARD, StratumPermanence.ETERNAL, StratumAdmission.BY_LINE, StratumActivity.REUNION, StratumContact.OPEN
        ),
    },
)
VALENCE_HOSTS: Mapping[StratumValence, tuple[DimensionKind, ...]] = total(
    StratumValence,
    {
        StratumValence.REWARD: (DimensionKind.CELESTIAL, DimensionKind.DIVINE_DOMAIN),
        StratumValence.NEUTRAL: (DimensionKind.UNDERWORLD,),
        StratumValence.PUNISHMENT: (DimensionKind.INFERNAL, DimensionKind.ABYSSAL),
        StratumValence.MIXED: (DimensionKind.UNDERWORLD, DimensionKind.SPIRIT),
    },
)
ACTIVITY_HOSTS: Mapping[StratumActivity, tuple[DimensionKind, ...] | None] = total(
    StratumActivity,
    {
        StratumActivity.REST: None,
        StratumActivity.SERVICE: (DimensionKind.DIVINE_DOMAIN, DimensionKind.CELESTIAL),
        StratumActivity.STRUGGLE: None,
        StratumActivity.REUNION: (DimensionKind.UNDERWORLD, DimensionKind.SPIRIT),
        StratumActivity.LEARNING: (DimensionKind.SPIRIT, DimensionKind.CELESTIAL),
        StratumActivity.DISSOLUTION: (DimensionKind.LIMBO, DimensionKind.UNDERWORLD),
    },
)
ADMISSION_PRIORITY: Mapping[StratumAdmission, int] = total(
    StratumAdmission,
    {
        StratumAdmission.BY_MANNER_OF_DEATH: 10,
        StratumAdmission.BY_FAITH: 15,
        StratumAdmission.BY_DEEDS: 20,
        StratumAdmission.BY_LINE: 40,
        StratumAdmission.BY_RITES: 45,
        StratumAdmission.BY_CHOICE: 60,
        StratumAdmission.ALL: 90,
    },
)


def hosts_for(valence: StratumValence, activity: StratumActivity) -> tuple[DimensionKind, ...]:
    return ACTIVITY_HOSTS[activity] or VALENCE_HOSTS[valence]


@dataclass(frozen=True)
class StratumSpec:
    label: str
    depth: int
    watery: bool
    bored: bool = False
    vents: bool = False
    caves: bool = False


STRATA: Mapping[UndergroundStratum, StratumSpec] = total(
    UndergroundStratum,
    {
        UndergroundStratum.AQUIFER: StratumSpec("Aquifer", 0, True, bored=True),
        UndergroundStratum.RESERVOIR: StratumSpec("Reservoir", 1, False, bored=True),
        UndergroundStratum.UNDER_OCEAN: StratumSpec("Ocean under the ice", 1, True, bored=True, vents=True),
        UndergroundStratum.CAVERN_UPPER: StratumSpec("Upper caverns", 2, False, caves=True),
        UndergroundStratum.CAVERN_MIDDLE: StratumSpec("Middle caverns", 3, False, caves=True),
        UndergroundStratum.CAVERN_DEEP: StratumSpec("Deep caverns", 4, False, caves=True),
        UndergroundStratum.MAGMA_SEA: StratumSpec("Magma sea", 5, False, vents=True),
        UndergroundStratum.HOLLOW_INTERIOR: StratumSpec("Hollow interior", 6, False),
        UndergroundStratum.DEEP_UNDERWORLD: StratumSpec("Deep underworld", 7, False),
    },
)
