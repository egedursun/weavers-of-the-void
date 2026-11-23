from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.customs import ReliefKind
from aerona.domain.enums.demography import CohortCondition

R = ReliefKind


@dataclass(frozen=True)
class ReliefSpec:
    label: str
    eases_poverty: bool
    takes_in: CohortCondition | None
    pays_loyalty: bool
    cost: str
    effect: str


RELIEF_KINDS: Mapping[ReliefKind, ReliefSpec] = total(
    ReliefKind,
    {
        R.GRANARY: ReliefSpec("Granary", True, None, False, "granary_cost", "granary_effect"),
        R.ALMS: ReliefSpec("Alms", True, None, False, "alms_cost", "alms_effect"),
        R.WORKHOUSE: ReliefSpec("Workhouse", True, None, False, "workhouse_cost", "workhouse_effect"),
        R.PARISH: ReliefSpec("Parish relief", True, None, False, "parish_cost", "parish_effect"),
        R.FOSTER_CARE: ReliefSpec("Foster care", False, CohortCondition.ORPHANED, False, "foster_care_cost", "foster_care_effect"),
        R.SICK_HOUSE: ReliefSpec("Sick house", False, CohortCondition.SICK, False, "sick_house_cost", "sick_house_effect"),
        R.PENSION: ReliefSpec("Pension", False, None, True, "pension_cost", "pension_effect"),
    },
)
