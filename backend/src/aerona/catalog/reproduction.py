from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.domain.enums.collective import RoleEligibility
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.polity import SexRule
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class SexKindSpec:
    label: str
    bears: bool
    begets: bool
    sexed: bool
    window: Callable[[Rules], int] | None
    word: str


K = SexKind
SEX_KINDS: Mapping[SexKind, SexKindSpec] = total(
    SexKind,
    {
        K.BEARER: SexKindSpec("Bears young", bears=True, begets=False, sexed=True, window=lambda rules: rules.fertility.bearer_window_end_pct, word="bearing"),
        K.BEGETTER: SexKindSpec(
            "Begets young", bears=False, begets=True, sexed=True, window=lambda rules: rules.fertility.begetter_window_end_pct, word="begetting"
        ),
        K.BOTH: SexKindSpec(
            "Bears and begets", bears=True, begets=True, sexed=True, window=lambda rules: rules.fertility.both_window_end_pct, word="bearing and begetting"
        ),
        K.NEITHER: SexKindSpec("Neither bears nor begets", bears=False, begets=False, sexed=True, window=None, word="neither bearing nor begetting"),
        K.NONE: SexKindSpec("Without sexes", bears=True, begets=False, sexed=False, window=lambda rules: rules.fertility.both_window_end_pct, word=""),
    },
)
BEARING_KINDS = frozenset(kind for kind, spec in SEX_KINDS.items() if spec.bears)
BEGETTING_KINDS = frozenset(kind for kind, spec in SEX_KINDS.items() if spec.begets)


@dataclass(frozen=True)
class SexSpec:
    sexes: tuple[SexKind, ...]
    split: bool

    @property
    def bearing(self) -> frozenset[SexKind]:
        return frozenset(sex for sex in self.sexes if SEX_KINDS[sex].bears)


TWO_KINDS = (K.BEARER, K.BEGETTER)
SEX_SYSTEMS = total(
    ReproductiveSystem,
    {
        ReproductiveSystem.TWO_SEX: SexSpec(TWO_KINDS, True),
        ReproductiveSystem.SEQUENTIAL: SexSpec(TWO_KINDS, True),
        ReproductiveSystem.CASTE: SexSpec(TWO_KINDS, True),
        ReproductiveSystem.AMBISEXUAL: SexSpec((K.BOTH,), False),
        ReproductiveSystem.ASEXUAL: SexSpec((K.NONE,), False),
    },
)

ELIGIBLE_WEIGHT = 1.0
PREFERRED_OTHER_WEIGHT = 0.25
BARRED_WEIGHT = 0.075


def rule_fit(wants_bearers: bool | None, only: bool, sex: SexKind) -> float | None:
    spec = SEX_KINDS[sex]
    if wants_bearers is None or not spec.sexed:
        return 1.0
    if spec.bears if wants_bearers else spec.begets:
        return 1.0
    return None if only else 0.5


ELIGIBILITY_NEEDS: Mapping[RoleEligibility, tuple[bool | None, bool]] = total(
    RoleEligibility,
    {
        RoleEligibility.ANY: (None, False),
        RoleEligibility.BEARERS_ONLY: (True, True),
        RoleEligibility.BEGETTERS_ONLY: (False, True),
        RoleEligibility.BEARERS_PREFERRED: (True, False),
        RoleEligibility.BEGETTERS_PREFERRED: (False, False),
    },
)
SEX_RULE_NEEDS: Mapping[SexRule, tuple[bool | None, bool]] = total(
    SexRule,
    {
        SexRule.ANY: (None, False),
        SexRule.BEARERS_ONLY: (True, True),
        SexRule.BEGETTERS_ONLY: (False, True),
        SexRule.BEARER_PREFERENCE: (True, False),
        SexRule.BEGETTER_PREFERENCE: (False, False),
    },
)


def weight_of(fit: float | None) -> float:
    if fit is None:
        return BARRED_WEIGHT
    return ELIGIBLE_WEIGHT if fit >= 1 else PREFERRED_OTHER_WEIGHT


ROLE_WEIGHTS: Mapping[RoleEligibility, Mapping[SexKind, float]] = MappingProxyType(
    {rule: MappingProxyType({sex: weight_of(rule_fit(*ELIGIBILITY_NEEDS[rule], sex)) for sex in SexKind}) for rule in RoleEligibility}
)


def sex_rule_fit(rule: SexRule, sex: SexKind) -> float | None:
    return rule_fit(*SEX_RULE_NEEDS[rule], sex)


def sex_shares(spec: SexSpec, bearer_pct: int) -> dict[SexKind, float]:
    if not spec.split:
        return {sex: 1 / len(spec.sexes) for sex in spec.sexes}
    bearers = bearer_pct / PERCENT
    return {K.BEARER: bearers, K.BEGETTER: 1 - bearers}


def kind_of_sex(value: str | None) -> SexKind:
    known = {kind.value for kind in SexKind}
    return SexKind(value) if value is not None and value in known else K.NONE
