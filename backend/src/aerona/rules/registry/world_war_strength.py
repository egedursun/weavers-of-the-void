from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class WorldWarStrengthRules:
    patron_strength_divisor: int = rule(8, 1, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Patron god's war contribution: god's strength / this number")
    war_father_mult: int = rule(2, 1, 20, RuleGroup.WAR_AND_DIPLOMACY, "The Warbringer power multiplies the patron contribution (times)")
    weapon_damage_divisor: int = rule(8, 1, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Weapon's war contribution: damage / this number")
    armor_protection_divisor: int = rule(10, 1, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Armor's war contribution: protection / this number")
    item_might_divisor: int = rule(20, 1, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Item might's war contribution: might / this number")
    warrior_threshold_pct: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "The warrior class adds war strength if above this share (%)")
    warrior_coeff_pct: int = rule(60, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Coefficient of warrior-class share on war strength (%)")
    cult_zealotry_coeff_pct: int = rule(60, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Zealotry coefficient of a cult's war strength (%)")
    default_zealotry: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Zealotry in war of a cult with no recorded zealotry")
    cult_follower_log_coeff: int = rule(8, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Coefficient of follower count (log10) on a cult's war strength")
    faction_sway_coeff_pct: int = rule(20, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Sway coefficient of a faction's war strength (%)")
    settlement_defense_coeff_pct: int = rule(80, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Walls (defense) coefficient of a settlement's war strength (%)")
    mortal_agility_divisor: int = rule(2, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Agility contribution to a mortal's war strength: agility / this number")
    species_strength_divisor: int = rule(
        2, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Strength contribution to a creature species' war strength: strength / this number"
    )
    default_stat: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Default strength of a community with no recorded war stat")
    warcraft_bonus: int = rule(12, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "War strength gain of those knowing the art of war")
    forbidden_knowledge_bonus: int = rule(15, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "War strength gain of those knowing forbidden knowledge")
    civilization_stage_bonus: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "War strength gain per civilization stage")
    ally_share_pct: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of strength allies add to a war (%)")
