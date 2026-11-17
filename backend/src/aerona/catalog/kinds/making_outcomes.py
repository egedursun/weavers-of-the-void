from collections.abc import Mapping
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.minds import MakingOutcome

WeightRule = Literal["unstable_weight", "empty_weight", "unintended_weight"]

MAKING_WEIGHTS: Mapping[MakingOutcome, WeightRule | None] = total(
    MakingOutcome,
    {
        MakingOutcome.AS_MEANT: None,
        MakingOutcome.UNSTABLE: "unstable_weight",
        MakingOutcome.EMPTY_SEAT: "empty_weight",
        MakingOutcome.UNINTENDED_WILL: "unintended_weight",
    },
)
