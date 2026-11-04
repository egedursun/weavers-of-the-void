from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class FactionsRules:
    faction_cap: int = rule(1, 0, 10, RuleGroup.CIVILIZATION, "Maximum factions founded spontaneously per epoch")
    faction_chance: int = rule(15, 0, 100, RuleGroup.CIVILIZATION, "A faction is founded within a community (%)")
    revolt_disband_chance: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "An uprising whose war ended disbands (%)")
    guild_min_merchant_pct: int = rule(11, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum merchant share of a community that founds a guild (%)")
    guild_min_prosperity: int = rule(45, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum prosperity of a community that founds a guild")
    guild_strength: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base strength of a merchant guild")
    guild_wealth: int = rule(55, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base wealth of a merchant guild")
    guild_sway: int = rule(45, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base sway of a merchant guild")
    council_min_priest_pct: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum priest share of a community that founds a priests' council (%)")
    council_strength: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base strength of a priests' council")
    council_wealth: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base wealth of a priests' council")
    council_sway: int = rule(55, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base sway of a priests' council")
    brotherhood_min_warrior_pct: int = rule(
        14, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum warrior share of a community that founds a warrior brotherhood (%)"
    )
    brotherhood_at_war_min_warrior_pct: int = rule(11, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum warrior share for a community at war (%)")
    brotherhood_strength: int = rule(55, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base strength of a warrior brotherhood")
    brotherhood_wealth: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base wealth of a warrior brotherhood")
    brotherhood_sway: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base sway of a warrior brotherhood")
    revolt_disband_min_age: int = rule(2, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Age of an uprising before it can disband (epochs)")
    revolt_disband_note_cap: int = rule(2, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Maximum disbanded uprisings written to the chronicle per epoch")
    faction_min_population: int = rule(1000, 0, 100000000, RuleGroup.WAR_AND_DIPLOMACY, "Minimum population of a community able to spawn a faction")
    faction_power_share_pct: int = rule(70, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Faction power level: share of its community's (%)")
    faction_max_power: int = rule(6, 1, 12, RuleGroup.WAR_AND_DIPLOMACY, "Maximum power level of an engine-founded faction")
    faction_stat_die: int = rule(25, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Die added to the stats of a new faction")
    faction_stat_shift: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Subtracted from a new faction's stats after the die")
    recruit_satisfaction_pct: int = rule(
        100, 0, 300, RuleGroup.WAR_AND_DIPLOMACY, "How much a discontented class raises the founding chance of its faction (%)"
    )
    recruit_strength_pct: int = rule(
        10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Strength a class faction gains each epoch per point of its class's discontent below the middle (%)"
    )
