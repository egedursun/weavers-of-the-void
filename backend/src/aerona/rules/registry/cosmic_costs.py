from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class CosmicCostsRules:
    ignite_star: int = rule(80, 0, 500, RuleGroup.COSMIC_ACTIONS, "Ignite a star")
    extinguish_star: int = rule(80, 0, 500, RuleGroup.COSMIC_ACTIONS, "Extinguish a star")
    seal_gate: int = rule(30, 0, 500, RuleGroup.COSMIC_ACTIONS, "Seal a gate")
    cleanse_leak: int = rule(80, 0, 500, RuleGroup.COSMIC_ACTIONS, "Cleanse a leak")
    forget_world: int = rule(20, 0, 500, RuleGroup.COSMIC_ACTIONS, "Forget a world")
    sky_event: int = rule(50, 0, 500, RuleGroup.COSMIC_ACTIONS, "Sky event")
    rekindle_dead_star: int = rule(60, 0, 500, RuleGroup.COSMIC_ACTIONS, "Rekindle a dead star")
    spirit_cloak: int = rule(15, 0, 500, RuleGroup.COSMIC_ACTIONS, "Cloak with spirit")
    legendary_expedition: int = rule(30, 0, 500, RuleGroup.COSMIC_ACTIONS, "Legendary expedition")
    create_galaxy: int = rule(300, 0, 5000, RuleGroup.COSMIC_ACTIONS, "Set a new galaxy among the others")
    create_cluster: int = rule(450, 0, 5000, RuleGroup.COSMIC_ACTIONS, "Gather a new cluster of galaxies")
    create_dimension: int = rule(600, 0, 5000, RuleGroup.COSMIC_ACTIONS, "Bring a new dimension into being")
