from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.powers import PowerHazard

Harm = Literal["wound", "stress", "exhaust", "mutate", "strain", "notice", "spill"]


@dataclass(frozen=True)
class Hazard:
    harm: Harm
    noted: bool = True


H = PowerHazard
POWER_HAZARDS: Mapping[PowerHazard, Hazard] = total(
    PowerHazard,
    {
        H.INJURY: Hazard("wound"),
        H.MADNESS: Hazard("stress"),
        H.LEAK: Hazard("spill", noted=False),
        H.ESCAPE: Hazard("strain"),
        H.DEPLETION: Hazard("spill", noted=False),
        H.WARPING: Hazard("mutate"),
        H.BURNOUT: Hazard("exhaust"),
        H.DEPENDENCY: Hazard("stress"),
        H.ATTENTION: Hazard("notice"),
    },
)
