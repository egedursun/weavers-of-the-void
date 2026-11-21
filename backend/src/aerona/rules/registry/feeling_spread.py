from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.HEROES_AND_MORTALS


@dataclass(frozen=True)
class FeelingSpreadRules(Spanned):
    per_bond_pct: int = rule(10, 0, 100, S, "Share of a strong feeling that passes along a bond to kin, friends and followers (%)")
    per_place_pct: int = rule(5, 0, 100, S, "Share of a place's leading feeling that each of its people catches (%)")
    fade_per_epoch: int = rule(20, 0, 100, S, "Share of a place's mood that fades in an epoch (%)")
    spread_floor: int = rule(30, 0, 100, S, "Strength a feeling needs before it spreads")
    crowd_pct: int = rule(20, 0, 100, S, "Share of a town's fear, anger or awe that feeds its crowd's mood (%)")
    charisma_reach_pct: int = rule(50, 0, 200, S, "How much further a feeling spreads from one of full charisma (%)")
    told_at: int = rule(50, 0, 100, S, "Strength at which a place's mood is told to have spread")
    caught_per_place: int = rule(12, 0, 1000, S, "People of one place who catch its leading feeling in an epoch at most")
    spreaders: int = rule(200, 0, 100000, S, "Strongest feelers whose feeling passes along their bonds in an epoch at most")
