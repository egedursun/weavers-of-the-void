from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ModifiersRules:
    decayed_add_drop_below: float = rule(0.5, 0, 100, RuleGroup.INTERCONNECTION, "An additive modifier is removed once decay shrinks it below this size")
    decayed_multiplier_drop_within_pct: int = rule(
        1, 0, 100, RuleGroup.INTERCONNECTION, "A multiplying modifier is removed once decay brings it this close to no effect (%)"
    )
    wonder_prosperity: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity a standing wonder adds to the community that holds it")
    wonder_piety: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Piety a standing wonder adds to the community that holds it")
    illness_strength_pct: int = rule(85, 0, 100, RuleGroup.INTERCONNECTION, "Strength and agility a lingering illness leaves (%)")
    withered_strength_pct: int = rule(80, 0, 100, RuleGroup.INTERCONNECTION, "Strength a withered limb leaves (%)")
    melancholy_intellect: int = rule(8, 0, 100, RuleGroup.INTERCONNECTION, "Intellect melancholy takes away")
    rage_strength: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Strength fits of rage lend")
    rage_intellect: int = rule(8, 0, 100, RuleGroup.INTERCONNECTION, "Intellect fits of rage take away")
    paranoia_charisma: int = rule(10, 0, 100, RuleGroup.INTERCONNECTION, "Charisma paranoia takes away")
    hunger_charisma: int = rule(10, 0, 100, RuleGroup.INTERCONNECTION, "Charisma an endless hunger takes away")
    void_taint_charisma: int = rule(15, 0, 100, RuleGroup.INTERCONNECTION, "Charisma the taint of the void takes away")
    chosen_charisma: int = rule(12, 0, 100, RuleGroup.INTERCONNECTION, "Charisma the mark of the chosen lends")
    brand_charisma: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Charisma a god's brand lends")


@dataclass(frozen=True)
class IncidentRules:
    thread_chain_min: int = rule(4, 2, 50, RuleGroup.INTERCONNECTION, "Length of a chain of causes at which the engine opens a story thread")
    chain_depth: int = rule(12, 2, 200, RuleGroup.INTERCONNECTION, "Most links of a cause chain followed back from an incident")
    threads_per_epoch: int = rule(2, 0, 20, RuleGroup.INTERCONNECTION, "Most story threads the engine opens from cause chains in one epoch")
