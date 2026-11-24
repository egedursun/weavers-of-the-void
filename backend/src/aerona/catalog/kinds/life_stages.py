from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.mortal import LifeStage

AgeLoss = Literal["mature_health_loss", "elder_health_loss", "ancient_health_loss"]


@dataclass(frozen=True)
class LifeStageSpec:
    recovers: bool
    counts_as_adult: bool
    age_loss: AgeLoss | None = None
    reached: str | None = None


S = LifeStage
LIFE_STAGES: Mapping[LifeStage, LifeStageSpec] = total(
    LifeStage,
    {
        S.INFANT: LifeStageSpec(recovers=True, counts_as_adult=False),
        S.CHILD: LifeStageSpec(recovers=True, counts_as_adult=False),
        S.YOUTH: LifeStageSpec(recovers=True, counts_as_adult=False),
        S.ADULT: LifeStageSpec(recovers=True, counts_as_adult=True, reached="adulthood"),
        S.ELDER: LifeStageSpec(recovers=False, counts_as_adult=True, age_loss="elder_health_loss", reached="old age"),
        S.ANCIENT: LifeStageSpec(recovers=False, counts_as_adult=False, age_loss="ancient_health_loss"),
        S.MATURE: LifeStageSpec(recovers=True, counts_as_adult=True, age_loss="mature_health_loss", reached="middle age"),
    },
)
