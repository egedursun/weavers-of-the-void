from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.customs import AgeGrade, GradeDuty
from aerona.domain.enums.mind import ValueAxis
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class DutySpec:
    label: str
    grade: AgeGrade
    axis: ValueAxis
    from_value: Callable[[Rules], int]


GRADE_DUTIES: Mapping[GradeDuty, DutySpec] = total(
    GradeDuty,
    {
        GradeDuty.WAR: DutySpec("War", AgeGrade.YOUNG_ADULTS, ValueAxis.MARTIAL, lambda rules: rules.age_sets.war_duty_from),
        GradeDuty.HERDING: DutySpec("Herding", AgeGrade.YOUTHS, ValueAxis.NATURE, lambda rules: rules.age_sets.herding_duty_from),
        GradeDuty.LABOUR: DutySpec("Labour", AgeGrade.YOUNG_ADULTS, ValueAxis.PERSEVERANCE, lambda rules: rules.age_sets.labour_duty_from),
        GradeDuty.COUNCIL: DutySpec("Council", AgeGrade.SENIOR_ELDERS, ValueAxis.TRADITION, lambda rules: rules.age_sets.council_duty_from),
    },
)
