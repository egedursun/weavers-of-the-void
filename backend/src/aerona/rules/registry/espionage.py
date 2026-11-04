from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class EspionageRules:
    spy_net_enemy_bonus_pct: int = rule(
        20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Bonus to setting up a spy network against an enemy or a tribute counterpart (%)"
    )
    spy_net_chance: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "An influential faction sets up a spy network (%)")
    spy_war_chance: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Captured spies lead to war (%)")
    spy_action_chance: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "The spy network acts this epoch (%)")
    spy_steal_knowledge_pct: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of spy actions that steal knowledge (otherwise sabotage) (%)")
    spy_min_sway: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum sway of a faction able to set up a spy network")
    spy_net_cap: int = rule(1, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Maximum new spy networks per epoch")
    spy_target_relation: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Coldness counted as a spy target (relation below minus this)")
    spy_capture_base_pct: int = rule(12, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base chance of spies being captured (%)")
    spy_capture_default: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Capture: value assumed if the target has no sway/defense")
    spy_capture_divisor: int = rule(400, 1, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Capture: target's sway / this number is added")
    spy_caught_relation_loss: int = rule(20, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Relation damage from captured spies")
    spy_sabotage_damage: int = rule(6, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Damage of sabotage to defense, strength and wealth")
    depth_gain: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Depth a spy network gains in an epoch, more under a skilled spymaster")
    intel_gain: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Intelligence a network at full depth gathers in an epoch")
    exposure_per_operation: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Exposure an operation leaves behind")
    exposure_decay: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Exposure that fades in a quiet epoch")
    counter_intel_pct: int = rule(100, 0, 300, RuleGroup.WAR_AND_DIPLOMACY, "Weight of the target's spymaster in catching spies (%)")
    assassinate_depth: int = rule(60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Depth a network needs to reach a ruler")
    incite_unrest: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Unrest agents stir up in a city")
    incite_uprising_unrest: int = rule(70, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Unrest at which incited townsfolk rise against their rulers")
    blackmail_wealth: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Wealth a blackmailed ruler pays")
    counterfeit_trust: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Trust a coin loses to false coins")
    granary_fire_pct: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Food a granary fire destroys (%)")
    wall_damage: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Wall condition lost to sappers in the night")
    poison_severity: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Severity of the sickness from poisoned wells")
