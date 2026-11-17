from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class SocietyKindsRules:
    rank_pull_pct: int = rule(10, 0, 100, G, "Share of a rank's privilege less its duty that moves its class's contentment each epoch, at full strength (%)")
    income_pct: int = rule(5, 0, 100, G, "Share of the earnings of the professions a people holds that its towns gain in prosperity each epoch (%)")
    mishap_pct: int = rule(20, 0, 100, G, "Share of a profession's risk that becomes the chance a worker of it is hurt each epoch, at full strength (%)")
    mishap_harm: int = rule(8, 0, 100, G, "Harm a worker takes when the work goes wrong")
    drift_pct: int = rule(10, 0, 100, G, "Share of the gap to its organisation kind that a faction's cohesion, secrecy and repute close each epoch (%)")
