from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.MIND


@dataclass(frozen=True)
class StressRules:
    break_threshold: int = rule(80, 0, 100, G, "Stress at which a mortal breaks")
    break_release: int = rule(40, 0, 100, G, "Stress a break releases")
    decay: int = rule(6, 0, 100, G, "Stress that eases each epoch")
    wound_per_severity: int = rule(4, 0, 100, G, "Stress each step of severity of a new wound adds")
    unmet_need_below: int = rule(30, 0, 100, G, "Need level below which an unmet need weighs on a mortal")
    unmet_need_stress: int = rule(3, 0, 100, G, "Stress each unmet need adds per epoch")
    loss_stress: int = rule(15, 0, 100, G, "Stress the death of kin adds")
    war_stress: int = rule(5, 0, 100, G, "Stress living through a war adds per epoch")
    duty_conflict_stress: int = rule(6, 0, 100, G, "Stress conflicting loyalties add per epoch")
    duty_gap: int = rule(40, 0, 100, G, "Gap between loyalty to liege and to people at which duties conflict")
    willpower_relief_pct: int = rule(50, 0, 200, G, "How much willpower dampens stress (%)")
    despair_suicide: int = rule(0, 0, 1, G, "Despair can end in suicide")
    despair_suicide_chance: int = rule(10, 0, 100, G, "Chance a despairing break ends in suicide when allowed (%)")
    revelation_seer_chance: int = rule(25, 0, 100, G, "Chance a revelation makes a mortal a seer (%)")
    flight_chance_pct: int = rule(100, 0, 400, G, "How likely a break is flight (%)")
    dissociation_gap: int = rule(20, 0, 100, G, "Strength of the gap in memory a being that dissociates under strain is left with")
    collapse_health: int = rule(15, 0, 100, G, "Health a being loses when its body fails under strain")
