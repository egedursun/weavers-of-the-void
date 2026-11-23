from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class GardenRules:
    upkeep: int = rule(10, 0, 10000, S, "Coin a garden, park, grove or cemetery costs its town each epoch")
    condition: int = rule(60, 0, 100, S, "Condition of a garden when it is laid out")
    tended: int = rule(5, 0, 100, S, "Condition a garden gains in an epoch its upkeep is paid")
    neglect: int = rule(10, 0, 100, S, "Condition a garden loses in an epoch its upkeep is not paid")
    pleasure_from: int = rule(70, 0, 100, S, "Prosperity from which a town lays out a pleasure garden")
    planted: int = rule(4, 0, 50, S, "Kinds of life of its land a garden takes in")
    beauty_per_garden: int = rule(8, 0, 100, S, "Beauty a mortal finds in each garden of its town in good condition")
    nature_per_garden: int = rule(8, 0, 100, S, "Nature a mortal finds in each garden of its town in good condition")
    physic_heal_pct: int = rule(20, 0, 100, S, "Share of the deaths and infections of wounds that a physic garden in good condition spares its town (%)")
    refuge_floor: int = rule(10, 0, 100, S, "Abundance below which a kind of life planted in a garden of its land does not fall")
    grove_standing: int = rule(3, 0, 100, S, "Love a sacred grove of a town gives each god of growing and wild things each epoch")
    prestige_pct: int = rule(50, 0, 100, S, "Share of the condition of a garden that its realm counts as grandeur (%)")
    botanic_knowledge: int = rule(5, 0, 50, S, "Spread a botanic garden in good condition adds each epoch to its town's knowledge of growing things")
    menagerie_prestige: int = rule(5, 0, 50, S, "Prestige a kept menagerie draws to its town through its visitors")
    botanic_from: int = rule(3, 0, 10, S, "Knowledge of growing things from which a prosperous town keeps a botanic garden for study")
    menagerie_escape_pct: int = rule(5, 0, 100, S, "Chance in an epoch that a neglected menagerie lets its beasts loose into its land (%)")
    son_cost: int = rule(30, 0, 1000, S, "Essence a son spends to lay out a garden in a town")
