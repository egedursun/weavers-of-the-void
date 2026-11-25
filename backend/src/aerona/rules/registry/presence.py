from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.CONTEXT_BUDGETS
A = RuleGroup.AGENTS_AND_MODEL
M = RuleGroup.MIND


@dataclass(frozen=True)
class PresenceRules:
    remembered_exchanges: int = rule(
        10, 1, 100, C, "Finished exchanges of an audience the summoned being keeps in mind, each the player's words and its answer"
    )
    max_steps: int = rule(24, 3, 200, A, "Model replies one exchange with a summoned being may take")
    audience_magnitude: int = rule(20, 1, 100, M, "Strength of the memory a being keeps of one exchange of an audience on the record, at its strongest feeling")
    audience_decay_pct: int = rule(10, 0, 100, M, "Share of an audience memory's strength that fades each epoch")
