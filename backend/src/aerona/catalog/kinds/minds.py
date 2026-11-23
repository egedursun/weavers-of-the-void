from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.minds import MindPurpose

Tended = Literal["mind", "town"]


@dataclass(frozen=True)
class PurposeSpec:
    will_pct: int
    tends: Tended | None = None
    column: str | None = None
    step: int = 0
    floor: int = 0


P = MindPurpose
MIND_PURPOSES: Mapping[MindPurpose, PurposeSpec] = total(
    MindPurpose,
    {
        P.TOOL: PurposeSpec(50),
        P.COMPANION: PurposeSpec(120, "mind", "maker_bond", 1, floor=-100),
        P.SERVANT: PurposeSpec(100),
        P.STEWARD: PurposeSpec(100, "town", "public_order", 1),
        P.SOVEREIGN: PurposeSpec(200),
        P.ORACLE: PurposeSpec(80),
        P.ARCHIVE: PurposeSpec(60, "mind", "stability", 1),
        P.GUARDIAN: PurposeSpec(90, "town", "crime", -1),
        P.FREE: PurposeSpec(150),
        P.SOLDIER: PurposeSpec(130, "town", "militia", 1),
        P.TEACHER: PurposeSpec(90),
    },
)
