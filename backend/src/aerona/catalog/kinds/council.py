from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.divine import VotingRule

SonWeight = Literal["fame", "level"]
ForeignWeight = Literal["faith", "power"]


@dataclass(frozen=True)
class VotingRuleSpec:
    son_weight: SonWeight | None = None
    foreign_weight: ForeignWeight | None = None
    foreign_divisor: int = 1
    everyone_agrees: bool = False


V = VotingRule
VOTING_RULES: Mapping[VotingRule, VotingRuleSpec] = total(
    VotingRule,
    {
        V.UNANIMITY: VotingRuleSpec(everyone_agrees=True),
        V.MAJORITY: VotingRuleSpec(),
        V.WEIGHTED_BY_STANDING: VotingRuleSpec("fame", "faith"),
        V.WEIGHTED_BY_RANK: VotingRuleSpec("level", "power", foreign_divisor=10),
    },
)
