from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class GodHandRules:
    decree_war_relation: int = rule(40, 0, 200, RuleGroup.INTERVENTION, "Community relation reduced when the god decrees war")
    decree_peace_relation: int = rule(20, 0, 200, RuleGroup.INTERVENTION, "Community relation added when the god decrees peace")
    decree_alliance_relation: int = rule(30, 0, 200, RuleGroup.INTERVENTION, "Community relation added when the god decrees an alliance")
    decree_trade_relation: int = rule(10, 0, 200, RuleGroup.INTERVENTION, "Community relation added when the god decrees trade")
    decree_expedition_pct: int = rule(10, 1, 100, RuleGroup.INTERVENTION, "Population joining an expedition decreed by the god (default %)")
    decree_expedition_max_pct: int = rule(30, 1, 100, RuleGroup.INTERVENTION, "Maximum population joining an expedition decreed by the god (%)")
    decree_climate_epochs: int = rule(4, 1, 100, RuleGroup.INTERVENTION, "Default duration of a climate age decreed by the god (epochs)")
    decree_climate_max_epochs: int = rule(50, 1, 1000, RuleGroup.INTERVENTION, "Longest climate age the god can decree (epochs)")
    rekindle_brightness: int = rule(75, 0, 100, RuleGroup.INTERVENTION, "Brightness of a rekindled star")
    rekindle_leak_drain: int = rule(20, 0, 100, RuleGroup.INTERVENTION, "Leak drawn from the worlds of a rekindled star")
    dispatch_donor_min_sons: int = rule(
        2, 1, 100, RuleGroup.INTERVENTION, "In automatic distribution, minimum active sons (including himself) that must remain on his world for a son to leave"
    )
    assignment_protection_epochs: int = rule(
        3, 0, 1000, RuleGroup.INTERVENTION, "Epochs during which automatic distribution does not touch a son the god manually sent to a world"
    )
    mortal_agents_per_world_cap: int = rule(12, 0, 1000, RuleGroup.INTERVENTION, "Maximum mortal agents that can be manually assigned per world")
    protector_bond_weight: int = rule(5, 0, 1000, RuleGroup.INTERVENTION, "Bond weight to the world a son protects when sons are distributed")
    deposit_power: int = rule(8, 1, 12, RuleGroup.INTERVENTION, "Power level of a cosmic resource deposit opened by the god")
    deposit_abundance: int = rule(80, 0, 100, RuleGroup.INTERVENTION, "Abundance of a cosmic resource deposit opened by the god")
    deposit_value: int = rule(95, 0, 100, RuleGroup.INTERVENTION, "Value of a cosmic resource deposit opened by the god")
    deposit_might: int = rule(85, 0, 100, RuleGroup.INTERVENTION, "Might of a cosmic resource deposit opened by the god")
