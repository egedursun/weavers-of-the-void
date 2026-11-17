from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.economy import FoeNature

SanctityRule = Literal["sanctity_undead_pct", "sanctity_cursed_pct", "sanctity_void_pct"]
CorruptionRule = Literal["corruption_void_pct"]


@dataclass(frozen=True)
class FoeBane:
    sanctity_rule: SanctityRule
    corruption_rule: CorruptionRule | None = None


FOE_BANES: Mapping[FoeNature, FoeBane] = total(
    FoeNature,
    {
        FoeNature.UNDEAD: FoeBane("sanctity_undead_pct"),
        FoeNature.CURSED: FoeBane("sanctity_cursed_pct"),
        FoeNature.VOID: FoeBane("sanctity_void_pct", "corruption_void_pct"),
    },
)
