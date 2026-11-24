from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.military import StarvationStage


@dataclass(frozen=True)
class StarvationSpec:
    starving: bool
    surrender_pct: int


STARVATION: Mapping[StarvationStage, StarvationSpec] = total(
    StarvationStage,
    {
        StarvationStage.NONE: StarvationSpec(starving=False, surrender_pct=0),
        StarvationStage.RATIONING: StarvationSpec(starving=False, surrender_pct=0),
        StarvationStage.FAMINE: StarvationSpec(starving=True, surrender_pct=100),
        StarvationStage.TABOO_BROKEN: StarvationSpec(starving=True, surrender_pct=200),
        StarvationStage.HUNGER_SICKNESS: StarvationSpec(starving=True, surrender_pct=150),
    },
)
