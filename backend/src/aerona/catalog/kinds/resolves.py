from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.operations import ResolveKind


@dataclass(frozen=True)
class ResolveSpec:
    ration: int = 1
    stress_pct: int = 100
    exposure_pct: int = 100
    others_rule: str | None = None
    others_sign: int = 0
    own_relief_rule: str | None = None
    keeps_watch: bool = False
    refuses_rest: bool = False
    flees: bool = False
    random: bool = False
    tends: bool = False
    lifts: bool = False


R = ResolveKind
RESOLVES: Mapping[ResolveKind, ResolveSpec] = total(
    ResolveKind,
    {
        R.STEADY: ResolveSpec(),
        R.PARANOID: ResolveSpec(refuses_rest=True),
        R.HOPELESS: ResolveSpec(ration=2, stress_pct=150),
        R.SELFISH: ResolveSpec(ration=2),
        R.ABUSIVE: ResolveSpec(others_rule="abusive_stress", others_sign=1),
        R.COURAGEOUS: ResolveSpec(others_rule="courage_relief", others_sign=-1),
        R.FOCUSED: ResolveSpec(keeps_watch=True),
        R.STALWART: ResolveSpec(exposure_pct=50, own_relief_rule="courage_relief"),
        R.FEARFUL: ResolveSpec(stress_pct=125, flees=True),
        R.IRRATIONAL: ResolveSpec(random=True),
        R.COMPASSIONATE: ResolveSpec(others_rule="compassionate_effect", others_sign=-1, tends=True),
        R.INSPIRED: ResolveSpec(others_rule="inspired_effect", others_sign=-1, lifts=True),
    },
)
