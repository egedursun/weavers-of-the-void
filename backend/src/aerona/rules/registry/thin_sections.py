from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

M = RuleGroup.MIND


@dataclass(frozen=True)
class CommunityRelationRules:
    held_pct: int = rule(100, 0, 300, M, "Share of a held part of a relation that the god's hand adds to the relation between two communities (%)")
    trade_value: int = rule(20, 0, 100, M, "Weight trade along a shared road gives the relation between two communities")
    faith_value: int = rule(20, 0, 100, M, "Weight sharing a god gives the relation, and holding none in common takes from it")
    language_value: int = rule(15, 0, 100, M, "Weight speaking one tongue gives the relation between two communities")
    rivalry_value: int = rule(40, 0, 100, M, "Weight an open feud takes from the relation between two communities")
    values_pct: int = rule(25, 0, 100, M, "Share of the gap between two communities' values that it takes from their relation (%)")
