from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

M = RuleGroup.MIND
G = RuleGroup.MORTALS
H = RuleGroup.HEROES_AND_MORTALS


@dataclass(frozen=True)
class PsycheRules:
    arousal_decay: int = rule(20, 0, 100, M, "Share by which a being's arousal settles back toward its middle each epoch (%)")
    calm_below: int = rule(40, 0, 100, M, "Arousal below which a being is calm")
    agitated_above: int = rule(65, 0, 100, M, "Arousal above which a being is agitated")
    agitated_rage_pct: int = rule(150, 0, 400, M, "How an agitated mood raises the chance that strain breaks a being (%)")
    calm_rage_pct: int = rule(60, 0, 400, M, "How a calm mood lowers the chance that strain breaks a being (%)")
    world_thought_cap: int = rule(40, 0, 1000, M, "Most beings at a place who take a thought from one happening there")


@dataclass(frozen=True)
class LifeCourseRules(Spanned):
    mature_decline_pct: int = rule(1, 0, 10, G, "Share of strength and endurance a mature being loses each year as its body begins to decline (%)")
    pitied_care: int = rule(10, 0, 100, G, "Care the kin of one whose death was pitied give the household left behind")


@dataclass(frozen=True)
class HonourRules:
    purity_breach: int = rule(10, 0, 100, H, "Standing a house of a purity model loses when one of its own is stained by a judged act")
