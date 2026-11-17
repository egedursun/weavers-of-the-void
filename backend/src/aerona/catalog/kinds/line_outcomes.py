from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.living import LineOutcome

WeightRule = Literal["unstable_weight", "sterile_weight", "side_weight", "dead_weight"]
StabilityRule = Literal["unstable_stability"]
DriftRule = Literal["unstable_drift"]


@dataclass(frozen=True)
class LineResult:
    weight_rule: WeightRule | None = None
    stability_rule: StabilityRule | None = None
    drift_rule: DriftRule | None = None
    sterile: bool = False
    side_effects: bool = False


L = LineOutcome
LINE_OUTCOMES: Mapping[LineOutcome, LineResult] = total(
    LineOutcome,
    {
        L.AS_MEANT: LineResult(),
        L.UNSTABLE: LineResult("unstable_weight", "unstable_stability", "unstable_drift"),
        L.STERILE: LineResult("sterile_weight", sterile=True),
        L.SIDE_EFFECTS: LineResult("side_weight", side_effects=True),
        L.NON_VIABLE: LineResult("dead_weight"),
        L.ESCAPED: LineResult(),
    },
)
