from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

M = RuleGroup.MIND


@dataclass(frozen=True)
class BeliefStateRules:
    decay: int = rule(15, 0, 100, M, "Confidence a belief loses each epoch it is not renewed")
    observe_confidence: int = rule(90, 0, 100, M, "Confidence of what an actor sees for itself")
    spy_confidence: int = rule(75, 0, 100, M, "Confidence of what spies report")
    rumour_confidence: int = rule(40, 0, 100, M, "Confidence of what rumour carries")
    deception_confidence: int = rule(60, 0, 100, M, "Confidence a deception plants")
    prior_pct: int = rule(100, 0, 400, M, "How much of the truth an actor guesses with no belief at all (%)")
    error_pct: int = rule(30, 0, 100, M, "Most a belief of low confidence strays from the truth when first formed (%)")
