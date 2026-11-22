from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.HOUSES


@dataclass(frozen=True)
class KinDynamicsRules(Spanned):
    favour_inheritance_pct: int = rule(20, 0, 100, S, "How far a parent's favour carries a child to the inheritance where the custom leaves a choice (%)")
    rivalry_from_favour_pct: int = rule(15, 0, 100, S, "Chance that each sibling of a favoured child turns rival (%)")
    split_threshold: int = rule(70, 0, 100, S, "Heat at which a rivalry splits a house, or a rivalry with a parent ends in disowning")
    reconcile_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a reversible disowning is mended (%)")
    favour_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a head of a house favours one child (%)")
    heat_step: int = rule(10, 0, 100, S, "Heat a rivalry gains in an epoch")
    disowning_tension: int = rule(15, 0, 100, S, "Tension each disowning not yet mended adds to its family, over the heat of its hottest rivalry")
    relation_loss: int = rule(5, 0, 100, S, "Regard rivals lose for each other in an epoch")
    elder_sway: int = rule(60, 0, 100, S, "Sway a surviving elder starts with over a house")
    sway_decay: int = rule(10, 0, 100, S, "Sway an elder loses in an epoch")
    overthrow_below: int = rule(30, 0, 100, S, "Sway below which the heir may overthrow an elder")
    overthrow_chance_pct: int = rule(25, 0, 100, S, "Chance in an epoch that the heir overthrows a weak elder (%)")
    step_standing: int = rule(50, 0, 100, S, "Standing step kin start with in a household")
    line_chance_pct: int = rule(50, 0, 100, S, "Chance that a disowned member founds a line of their own (%)")
