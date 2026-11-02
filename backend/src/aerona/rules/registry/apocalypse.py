from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ApocalypseRules:
    godless: int = rule(2, 0, 50, RuleGroup.APOCALYPSE, "Each godless community advances the clock")
    cursed: int = rule(1, 0, 50, RuleGroup.APOCALYPSE, "Each cursed entity advances the clock")
    restless_spirit: int = rule(2, 0, 50, RuleGroup.APOCALYPSE, "Each restless spirit advances the clock")
    restless_threshold: int = rule(60, 0, 100, RuleGroup.APOCALYPSE, "Unrest of a spirit counted as restless")
    hostility_divisor: int = rule(1, 1, 100, RuleGroup.APOCALYPSE, "Every this many ongoing community wars advance the clock by 1 (fractions accumulate)")
    rebel_son: int = rule(4, 0, 50, RuleGroup.APOCALYPSE, "Each rebel son advances the clock")
    miracle: int = rule(3, 0, 50, RuleGroup.APOCALYPSE, "Each miracle pushes the clock back")
    faith_divisor: int = rule(40, 1, 10000, RuleGroup.APOCALYPSE, "Every this much faith pushes the clock back by 1")
    faith_cap: int = rule(4, 0, 100, RuleGroup.APOCALYPSE, "Maximum push-back of the clock by faith in one epoch")
    peace: int = rule(2, 0, 50, RuleGroup.APOCALYPSE, "An epoch with no war pushes the clock back")
    wonder_cap: int = rule(3, 0, 50, RuleGroup.APOCALYPSE, "Maximum push-back of the clock by wonders (1 per wonder)")
    temple_cap: int = rule(2, 0, 50, RuleGroup.APOCALYPSE, "Maximum push-back of the clock by temples (1 per two temples)")
    golden_age: int = rule(3, 0, 50, RuleGroup.APOCALYPSE, "Each world in a golden age pushes the clock back")
    warning_1_pct: int = rule(50, 1, 100, RuleGroup.APOCALYPSE, "Point at which the first omen comes (% of threshold)")
    warning_2_pct: int = rule(80, 1, 100, RuleGroup.APOCALYPSE, "Point at which the final warning comes (% of threshold)")
    after_calling_pct: int = rule(60, 0, 100, RuleGroup.APOCALYPSE, "Where the clock falls when the apocalypse turns into the Calling (% of threshold)")
    after_ruin_pct: int = rule(40, 0, 100, RuleGroup.APOCALYPSE, "Where the clock falls when the apocalypse destroys (% of threshold)")
