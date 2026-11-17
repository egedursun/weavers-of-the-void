from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.integrity import SectionState

Tier = Literal["damaged", "disabled", "destroyed"]


@dataclass(frozen=True)
class SectionStateSpec:
    function_pct: int
    minor_function_pct: int
    tier: Tier | None


SECTION_STATES: Mapping[SectionState, SectionStateSpec] = total(
    SectionState,
    {
        SectionState.SOUND: SectionStateSpec(function_pct=100, minor_function_pct=100, tier=None),
        SectionState.DAMAGED: SectionStateSpec(function_pct=75, minor_function_pct=75, tier="damaged"),
        SectionState.DISABLED: SectionStateSpec(function_pct=0, minor_function_pct=25, tier="disabled"),
        SectionState.DESTROYED: SectionStateSpec(function_pct=0, minor_function_pct=0, tier="destroyed"),
    },
)
