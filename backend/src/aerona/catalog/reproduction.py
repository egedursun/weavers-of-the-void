from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.domain.enums.collective import RoleEligibility
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.demography import Sex


@dataclass(frozen=True)
class SexSpec:
    sexes: tuple[Sex, ...]
    bearing: frozenset[Sex]
    split: bool


SEX_SYSTEMS = total(
    ReproductiveSystem,
    {
        ReproductiveSystem.TWO_SEX: SexSpec((Sex.FEMALE, Sex.MALE), frozenset({Sex.FEMALE}), True),
        ReproductiveSystem.SEQUENTIAL: SexSpec((Sex.FEMALE, Sex.MALE), frozenset({Sex.FEMALE}), True),
        ReproductiveSystem.CASTE: SexSpec((Sex.FEMALE, Sex.MALE), frozenset({Sex.FEMALE}), True),
        ReproductiveSystem.AMBISEXUAL: SexSpec((Sex.OTHER,), frozenset({Sex.OTHER}), False),
        ReproductiveSystem.ASEXUAL: SexSpec((Sex.OTHER,), frozenset({Sex.OTHER}), False),
    },
)

ELIGIBLE_WEIGHT = 1.0
PREFERRED_OTHER_WEIGHT = 0.25
BARRED_WEIGHT = 0.075

ROLE_WEIGHTS = total(
    RoleEligibility,
    {
        RoleEligibility.ANY: {Sex.FEMALE: ELIGIBLE_WEIGHT, Sex.MALE: ELIGIBLE_WEIGHT, Sex.OTHER: ELIGIBLE_WEIGHT},
        RoleEligibility.FEMALE_ONLY: {Sex.FEMALE: ELIGIBLE_WEIGHT, Sex.MALE: BARRED_WEIGHT, Sex.OTHER: BARRED_WEIGHT},
        RoleEligibility.MALE_ONLY: {Sex.FEMALE: BARRED_WEIGHT, Sex.MALE: ELIGIBLE_WEIGHT, Sex.OTHER: BARRED_WEIGHT},
        RoleEligibility.FEMALE_PREFERRED: {Sex.FEMALE: ELIGIBLE_WEIGHT, Sex.MALE: PREFERRED_OTHER_WEIGHT, Sex.OTHER: PREFERRED_OTHER_WEIGHT},
        RoleEligibility.MALE_PREFERRED: {Sex.FEMALE: PREFERRED_OTHER_WEIGHT, Sex.MALE: ELIGIBLE_WEIGHT, Sex.OTHER: PREFERRED_OTHER_WEIGHT},
    },
)


def sex_shares(spec: SexSpec, female_pct: int) -> dict[Sex, float]:
    if not spec.split:
        return {sex: 1 / len(spec.sexes) for sex in spec.sexes}
    female = female_pct / PERCENT
    return {Sex.FEMALE: female, Sex.MALE: 1 - female}
