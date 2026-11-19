from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class FacetRules:
    drift_pct: int = rule(25, 1, 100, G, "Share of the gap to its sources a practice closes each epoch (%)")
    effect_pct: int = rule(100, 0, 400, G, "Scale of what a fully kept practice does to its community each epoch (%)")
    rooted_level: int = rule(50, 1, 100, G, "Level at which a practice counts as rooted in its community")
    faded_level: int = rule(10, 0, 99, G, "Level at or below which a practice counts as faded")
    channel_cap: int = rule(15, 0, 100, G, "Most that all practices together move one value of a community each epoch")
