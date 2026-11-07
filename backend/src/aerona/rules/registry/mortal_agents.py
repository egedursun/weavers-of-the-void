from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class MortalAgentsRules:
    action_points: int = rule(3, 1, 6, RuleGroup.MORTAL_AGENTS, "Mortal action points")
    agents_per_epoch: int = rule(10, 0, 1000, RuleGroup.MORTAL_AGENTS, "Mortal agents per epoch")
    max_turns: int = rule(12, 4, 20, RuleGroup.MORTAL_AGENTS, "Mortal turn limit (steps)")
    creature_min_intelligence: int = rule(55, 0, 100, RuleGroup.MORTAL_AGENTS, "Minimum intelligence for a creature to play as an agent")
