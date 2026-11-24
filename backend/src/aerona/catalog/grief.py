from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.mind import GriefStage

G = GriefStage


@dataclass(frozen=True)
class GriefSpec:
    label: str
    order: int
    open: bool
    angry: bool = False
    yearning: bool = False
    bargains: bool = False


GRIEF_STAGES: Mapping[GriefStage, GriefSpec] = total(
    GriefStage,
    {
        G.SHOCK: GriefSpec("Shock", 0, open=True),
        G.ANGER: GriefSpec("Anger", 1, open=True, angry=True),
        G.BARGAINING: GriefSpec("Bargaining", 2, open=True, bargains=True),
        G.MOURNING: GriefSpec("Mourning", 3, open=True),
        G.YEARNING: GriefSpec("Yearning", 4, open=True, yearning=True),
        G.ACCEPTANCE: GriefSpec("Acceptance", 5, open=False),
        G.COMPLICATED: GriefSpec("Complicated", 6, open=False),
    },
)
OPEN_GRIEF_STAGES = tuple(stage for stage, spec in sorted(GRIEF_STAGES.items(), key=lambda item: item[1].order) if spec.open)
