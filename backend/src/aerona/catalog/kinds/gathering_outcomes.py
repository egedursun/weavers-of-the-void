from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.gathering import GatheringOutcome
from aerona.domain.enums.mind import ThoughtKind


@dataclass(frozen=True)
class GatheringResult:
    disrupts: bool = False
    thought: ThoughtKind | None = None


G = GatheringOutcome
GATHERING_RESULTS: Mapping[GatheringOutcome, GatheringResult] = total(
    GatheringOutcome,
    {
        G.CONVIVIAL: GatheringResult(),
        G.UNEVENTFUL: GatheringResult(),
        G.QUARRELSOME: GatheringResult(),
        G.VIOLENT: GatheringResult(disrupts=True),
        G.MASSACRE: GatheringResult(disrupts=True, thought=ThoughtKind.WITNESSED_ATROCITY),
    },
)
