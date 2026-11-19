from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.POPULATION_AND_GROWTH


@dataclass(frozen=True)
class YouthRules:
    delinquency_base_pct: int = rule(
        5, 0, 100, S, "Chance each epoch a youth group turns to delinquency, before poverty, weak order, freedom and its purpose weigh in"
    )
    recruitment_pct: int = rule(20, 0, 100, S, "Chance each epoch a member of a youth group of crime or politics is drawn into a gang or movement of its town")
    service_cooption_pct: int = rule(30, 0, 100, S, "Chance each epoch a realm draws a youth group of mischief, crime or politics into service")
    form_size: int = rule(3, 1, 100, S, "Youths without a group in a town at which they form one")
    join_pct: int = rule(50, 0, 100, S, "Chance each epoch a youth without a group joins one in its town")
    group_effect: int = rule(2, 0, 100, S, "Points a youth group moves its town's order, crime or unrest each epoch by its purpose")
    member_effect: int = rule(2, 0, 100, S, "Points a youth group moves its members' values or stress each epoch by its purpose")
    delinquency_crime: int = rule(5, 0, 100, S, "Crime a town gains from one delinquency of a youth group")
