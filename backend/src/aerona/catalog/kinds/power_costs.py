from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.powers import PowerCost

Draw = Literal["stress", "age", "wealth", "renown", "mutation", "fortune", "surroundings", "patron", "souls", "nothing"]


@dataclass(frozen=True)
class CostDraw:
    draws: Draw
    mortals_only: bool = False


C = PowerCost
POWER_COSTS: Mapping[PowerCost, CostDraw] = total(
    PowerCost,
    {
        C.ESSENCE: CostDraw("patron"),
        C.HP: CostDraw("stress"),
        C.FATIGUE: CostDraw("stress"),
        C.STRAIN: CostDraw("stress"),
        C.LIFESPAN: CostDraw("age", mortals_only=True),
        C.MEMORY: CostDraw("stress"),
        C.EMOTION: CostDraw("stress"),
        C.SANITY: CostDraw("stress"),
        C.REAGENT: CostDraw("wealth"),
        C.MATERIAL: CostDraw("wealth"),
        C.VIS: CostDraw("wealth"),
        C.BELIEF: CostDraw("renown", mortals_only=True),
        C.RENOWN: CostDraw("renown", mortals_only=True),
        C.OATH_STANDING: CostDraw("renown", mortals_only=True),
        C.DEBT: CostDraw("wealth"),
        C.SOUL: CostDraw("souls"),
        C.TIME: CostDraw("age", mortals_only=True),
        C.SURROUNDINGS: CostDraw("surroundings"),
        C.LUCK: CostDraw("fortune"),
        C.WARPING: CostDraw("mutation"),
        C.NONE: CostDraw("nothing"),
    },
)
