from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.body import BodyRegion, StrikeStyle


@dataclass(frozen=True)
class StrikeStyleSpec:
    lean: tuple[tuple[BodyRegion, str], ...] = ()
    whole: bool = False


B = BodyRegion
S = StrikeStyle
STRIKE_STYLES: Mapping[StrikeStyle, StrikeStyleSpec] = total(
    StrikeStyle,
    {
        S.NORMAL: StrikeStyleSpec(),
        S.WHOLE: StrikeStyleSpec(whole=True),
        S.TRAMPLE: StrikeStyleSpec(((B.LEGS, "trample_legs_pct"), (B.TORSO, "trample_torso_pct"))),
        S.AERIAL: StrikeStyleSpec(((B.HEAD, "aerial_head_pct"), (B.WINGS, "aerial_wings_pct"))),
        S.LOW: StrikeStyleSpec(((B.LEGS, "low_legs_pct"),)),
        S.RANGED: StrikeStyleSpec(((B.TORSO, "ranged_torso_pct"), (B.HEAD, "ranged_head_pct"))),
        S.BURROWING: StrikeStyleSpec(((B.LEGS, "burrow_legs_pct"), (B.TAIL, "burrow_legs_pct"))),
        S.ENGULFING: StrikeStyleSpec(whole=True),
        S.FROM_HIDING: StrikeStyleSpec(((B.HEAD, "hidden_head_pct"), (B.TORSO, "hidden_torso_pct"))),
    },
)
