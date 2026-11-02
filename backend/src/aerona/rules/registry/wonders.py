from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class WondersRules:
    min_splendor: int = rule(80, 0, 100, RuleGroup.CIVILIZATION, "Minimum splendor of a structure counted as a wonder")
    min_power: int = rule(7, 0, 12, RuleGroup.CIVILIZATION, "Minimum power level of a structure counted as a wonder")
    prosperity: int = rule(2, 0, 100, RuleGroup.CIVILIZATION, "Per-epoch prosperity contribution of a wonder to its owner")
    faith: int = rule(1, 0, 100, RuleGroup.CIVILIZATION, "Per-epoch faith contribution of a wonder to its owner")
    renown: int = rule(1, 0, 100, RuleGroup.CIVILIZATION, "Per-epoch renown to the god of a wonder's owner")
    envy_threshold: int = rule(10, -100, 100, RuleGroup.WAR_AND_DIPLOMACY, "A neighbour below this relation envies the wonder")
    envy_relation_loss: int = rule(2, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Relation loss of an envious neighbour (per epoch)")
    war_relation: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Hostility of a neighbour going to war over a wonder (relation minus this)")
    envy_war_chance: int = rule(
        2, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A jealous neighbour declares the wonder's owner its enemy (%; counts against the epoch's declaration cap)"
    )
