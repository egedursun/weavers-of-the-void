from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.dominion import BeliefStance

PullRule = Literal["embrace_pull_pct", "yield_pull_pct"]
FameRule = Literal["embrace_fame"]


@dataclass(frozen=True)
class StanceToBelief:
    pull_rule: PullRule | None = None
    fame_rule: FameRule | None = None
    resists: bool = False


BELIEF_STANCES: Mapping[BeliefStance, StanceToBelief] = total(
    BeliefStance,
    {
        BeliefStance.YIELD: StanceToBelief(pull_rule="yield_pull_pct"),
        BeliefStance.RESIST: StanceToBelief(resists=True),
        BeliefStance.EMBRACE: StanceToBelief(pull_rule="embrace_pull_pct", fame_rule="embrace_fame"),
    },
)
