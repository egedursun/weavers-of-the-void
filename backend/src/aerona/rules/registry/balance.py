from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class BalanceRules:
    creator_essence_regen: int = rule(20, 0, 1000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Creator's essence per epoch")
    creator_essence_soft_cap: int = rule(800, 0, 100000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Soft cap of the Creator's essence")
    resurrection: int = rule(150, 0, 1000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Resurrection")
    create_world: int = rule(120, 0, 1000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Create a world")
    birth_world: int = rule(70, 0, 1000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Birth a world (son)")
    council: int = rule(20, 0, 1000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Council")
    dream: int = rule(8, 0, 1000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Dream sent by the Creator to a mortal")
    awaken_peoples: int = rule(35, 0, 1000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Awaken the peoples")
    apocalypse_threshold: int = rule(100, 1, 1000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Apocalypse threshold (apocalypse happens when the clock reaches this)")
    apocalypse_speed: int = rule(1, 0, 300, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Apocalypse speed (%; 0 = clock stops)")
    suppress_revolt: int = rule(20, 0, 1000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Suppress an uprising")
    creator_starting_essence: int = rule(150, 0, 1000, RuleGroup.MAJOR_ACTIONS_AND_ESSENCE, "Creator's starting essence in a new cosmos")
