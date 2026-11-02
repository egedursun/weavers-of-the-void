from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class CampaignsRules:
    cult_soldier_pct: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of followers joining a cult army (%)")
    faction_soldiers_per_strength: int = rule(60, 0, 10000, RuleGroup.WAR_AND_DIPLOMACY, "Faction army: soldiers per military-strength point")
    faction_soldiers_per_wealth: int = rule(20, 0, 10000, RuleGroup.WAR_AND_DIPLOMACY, "Faction army: soldiers per wealth point")
    faction_default_strength: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Strength assumed for a faction with unknown strength")
    faction_default_wealth: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Wealth assumed for a faction with unknown wealth")
    cult_default_followers: int = rule(
        100, 0, 1000000, RuleGroup.WAR_AND_DIPLOMACY, "Followers assumed in the army calculation for a cult with unknown followers"
    )
    default_population: int = rule(
        1000, 0, 10000000, RuleGroup.WAR_AND_DIPLOMACY, "Population assumed in the army calculation for a people or city with unknown population"
    )
    default_zealotry: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Zealotry assumed in the holy guard's morale for a cult with unknown zealotry")
    min_soldier_pct: int = rule(4, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum share of population in a people's or city's army (%)")
    army_power_min: int = rule(2, 1, 12, RuleGroup.WAR_AND_DIPLOMACY, "Minimum power level of an army")
    army_power_max: int = rule(8, 1, 12, RuleGroup.WAR_AND_DIPLOMACY, "Maximum power level of an army")
    army_min_soldiers: int = rule(30, 1, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Minimum soldiers in an army")
    idle_army_return_pct: int = rule(
        25,
        0,
        100,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Share of an army without an ongoing war that goes home each epoch (%; a deathless army keeps watch and never stands down)",
    )
    idle_army_disband_below: int = rule(50, 0, 1000000, RuleGroup.WAR_AND_DIPLOMACY, "An idle army below this many soldiers disbands")
    army_morale_base: int = rule(55, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base morale of a new army")
    army_morale_die: int = rule(25, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Die added to a new army's morale (1\u2013N)")
    holy_guard_zealotry_divisor: int = rule(5, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Holy guard morale: zealotry / this number")
    army_equipment_base: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base equipment of a new army")
    army_equipment_weapon_mult: int = rule(2, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Multiplier of weapon strength on equipment")
    army_equipment_metallurgy: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Equipment bonus for those who know metallurgy")
    army_experience_warcraft: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Initial experience of an army that knows the art of war")
    army_experience: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Initial experience of a new army")
    war_event_initial_power: int = rule(4, 1, 12, RuleGroup.WAR_AND_DIPLOMACY, "Initial power level of a war record")
    war_initial_severity: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Initial severity of a war")
    siege_min_defense: int = rule(55, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum defense of a settlement that undergoes a siege")
    strength_community_share_pct: int = rule(60, 0, 500, RuleGroup.WAR_AND_DIPLOMACY, "Share of the community's military strength entering battle strength (%)")
    strength_size_log_mult: int = rule(14, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Battle strength: multiplier of the logarithm of soldier count")
    strength_morale_divisor: int = rule(3, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Battle strength: morale / this number")
    strength_equipment_divisor: int = rule(4, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Battle strength: equipment / this number")
    strength_experience_divisor: int = rule(5, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Battle strength: experience / this number")
    strength_commander_divisor: int = rule(12, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Battle strength: commander's strength+intellect+charisma / this number")
    battle_die: int = rule(20, 1, 200, RuleGroup.WAR_AND_DIPLOMACY, "Battle luck die (1\u2013N)")
    battle_die_mult: int = rule(2, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Multiplier of the battle luck die")
    severity_per_battle: int = rule(8, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "War severity increase per battle")
    severity_diff_divisor: int = rule(10, 1, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Contribution of strength difference to severity: difference / this number")
    war_power_min: int = rule(2, 1, 12, RuleGroup.WAR_AND_DIPLOMACY, "Minimum power level of a war record")
    war_power_max: int = rule(9, 1, 12, RuleGroup.WAR_AND_DIPLOMACY, "Maximum power level of a war record")
    war_power_battle_interval: int = rule(2, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "The war record's power level rises once every this many battles")
    war_power_step: int = rule(1, 0, 12, RuleGroup.WAR_AND_DIPLOMACY, "Power-level increase of the war record at that battle")
    breach_diff_divisor: int = rule(60, 1, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Chance to breach walls: strength difference / this number")
    breach_starving_supplies: int = rule(15, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "A besieged city with supplies below this counts as starving")
    breach_starving_bonus_pct: int = rule(35, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Bonus to the chance of breaching a starving city's walls (%)")
    breach_min_pct: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Floor of the wall-breach chance (%)")
    breach_max_pct: int = rule(85, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Cap of the wall-breach chance (%)")
    siege_repelled_morale_loss: int = rule(6, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Attacker's morale loss when a siege is repelled")
    breach_defense_loss: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "City's defense loss when its walls are breached")
    breach_war_score: int = rule(3, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Contribution of breaching walls to the war score")
    siege_population_kept_pct: int = rule(94, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Population remaining in the city during a siege (%)")
    siege_prosperity_loss: int = rule(6, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Prosperity removed from the city by a siege")
    siege_supply_loss: int = rule(20, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Supplies removed from the city's granary by a siege")
    siege_attacker_morale_loss: int = rule(4, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Attacker's morale loss in an ongoing siege")
    siege_default_supplies: int = rule(50, 0, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Supplies assumed for a besieged city with no granary record")
    siege_default_population: int = rule(100, 0, 10000000, RuleGroup.WAR_AND_DIPLOMACY, "Population assumed for a besieged city with no population record")
    great_victory_diff: int = rule(35, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Strength difference counted as a great victory")
    great_victory_score: int = rule(2, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Contribution of a great victory to the war score")
    loser_base_loss_pct: int = rule(12, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base loss of the defeated army (%)")
    loser_extra_loss_max_pct: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Maximum extra loss of the defeated army from strength difference (%)")
    loser_extra_loss_divisor: int = rule(220, 1, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Defeated extra loss: strength difference / this number")
    winner_base_loss_pct: int = rule(4, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base loss of the victorious army (%)")
    winner_extra_loss_max_pct: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Maximum extra loss of the victorious army from strength difference (%)")
    winner_extra_loss_divisor: int = rule(600, 1, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Victor extra loss: strength difference / this number")
    loser_morale_loss: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Morale loss of the defeated army")
    loser_morale_diff_divisor: int = rule(8, 1, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Defeated extra morale loss: strength difference / this number")
    winner_morale_gain: int = rule(4, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Morale gain of the victorious army")
    winner_experience_gain: int = rule(6, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Experience gain of the victorious army")
    loser_experience_gain: int = rule(3, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Experience gain of the defeated army")
    community_loss_divisor: int = rule(5, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Defeated community's population loss: army loss / this number")
    loser_prosperity_loss: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Prosperity and wealth loss of the defeated community")
    winner_wealth_gain: int = rule(3, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Wealth gain of the victorious community")
    battle_relation: int = rule(8, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Relation reduced by a battle (points)")
    patron_renown_per_battle: int = rule(2, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Renown per battle of the victor's patron god")
    patron_xp_per_battle: int = rule(8, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "XP per battle of the victor's patron god")
    patron_relation_loss: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Relation between the two patron gods reduced by a battle")
    battle_event_power_divisor: int = rule(20, 1, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Battle record power: strength difference / this number")
    battle_event_power_min: int = rule(2, 1, 12, RuleGroup.WAR_AND_DIPLOMACY, "Minimum power level of a battle record")
    battle_event_power_max: int = rule(7, 1, 12, RuleGroup.WAR_AND_DIPLOMACY, "Maximum power level of a battle record")
    battle_event_severity_base: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base severity of a battle record")
    battle_severity_ceiling: int = rule(
        95, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Battle severity approaches this ceiling as the strength gap grows, never pinned to 100"
    )
    battle_severity_half_gap: int = rule(
        60, 1, 10000, RuleGroup.WAR_AND_DIPLOMACY, "Battle severity is halfway between its base and ceiling at this strength gap"
    )
    duel_agility_divisor: int = rule(2, 1, 100, RuleGroup.HEROES_AND_MORTALS, "Duel strength: agility / this number")
    duel_weapon_mult: int = rule(2, 0, 20, RuleGroup.HEROES_AND_MORTALS, "Multiplier of weapon strength in a duel")
    duel_die: int = rule(20, 1, 200, RuleGroup.HEROES_AND_MORTALS, "Duel luck die (1\u2013N)")
    duel_die_mult: int = rule(2, 0, 20, RuleGroup.HEROES_AND_MORTALS, "Multiplier of the duel luck die")
    duel_winner_charisma: int = rule(6, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Charisma gain of the duel winner")
    duel_loser_hp_loss: int = rule(40, 0, 1000, RuleGroup.HEROES_AND_MORTALS, "HP loss of the duel loser")
    hero_default_hp: int = rule(100, 1, 100000, RuleGroup.HEROES_AND_MORTALS, "HP assumed when wounding a hero with no HP record")
    disband_morale: int = rule(12, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "An army below this morale disbands")
    disband_soldiers: int = rule(30, 0, 100000, RuleGroup.WAR_AND_DIPLOMACY, "An army below this many soldiers disbands")
    decisive_score: int = rule(3, 1, 50, RuleGroup.WAR_AND_DIPLOMACY, "Decisive score that ends the war")
    exhaustion_min_battles: int = rule(4, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Number of battles at which exhaustion peace becomes possible")
    conquest_relation: int = rule(25, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Relation reduced by conquest (points)")
    tribute_relation: int = rule(10, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Relation reduced by being bound to tribute (points)")
    white_peace_relation: int = rule(8, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Relation bonus of a white peace (points)")
    tribute_end_relation: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Relation bonus when tribute ends (points)")
    tribute_revolt_relation: int = rule(15, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Relation reduced by a tribute revolt (points)")
    ransom_min_wealth: int = rule(30, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Minimum wealth of a homeland able to pay ransom")
    ransom_min_prosperity: int = rule(50, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Minimum prosperity of a homeland able to pay ransom")
    ransom_cost: int = rule(12, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Wealth and prosperity cost of a ransom")
    ransom_relation: int = rule(5, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Relation bonus of a ransom (points)")
    escape_agility_divisor: int = rule(250, 1, 100000, RuleGroup.HEROES_AND_MORTALS, "Captive's escape chance: agility / this number")
    escape_intellect_divisor: int = rule(400, 1, 100000, RuleGroup.HEROES_AND_MORTALS, "Captive's escape chance: intellect / this number")
    captive_default_stat: int = rule(30, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Value assumed for a captive with unknown agility or intellect")
    execution_relation: int = rule(70, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Below this hostility (negative points) the captive may be executed")
    captive_defection_epochs: int = rule(3, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Captivity duration after which the captive may switch sides (epochs)")
    battle_record_min_diff: int = rule(
        30, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Strength difference required for a separate battle record (sieges are always recorded)"
    )
    battle_cap: int = rule(
        6, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Maximum battles per epoch (in ongoing wars; a new war's first clash counts against new_war_cap)"
    )
    mobilization: int = rule(
        1,
        0,
        1,
        RuleGroup.WAR_AND_DIPLOMACY,
        "A new war's first epoch is mobilization: armies gather, first clash the next epoch (1: on, 0: clash in the epoch of declaration)",
    )
    new_war_cap: int = rule(3, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Maximum new wars per epoch (from enemy pairs; only below the war caps)")
    battle_chance: int = rule(70, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Enemies clash this epoch (%)")
    battle_chance_war_ban: int = rule(35, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Clash while a war ban is in effect (%)")
    tribute_epochs: int = rule(4, 1, 30, RuleGroup.WAR_AND_DIPLOMACY, "Tribute duration (epochs)")
    tribute_flow: int = rule(2, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Prosperity and wealth transferred per epoch by tribute")
    tribute_goods_pct: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of goods transferred by tribute (%)")
    tribute_revolt_strength_pct: int = rule(125, 100, 500, RuleGroup.WAR_AND_DIPLOMACY, "Strength ratio required for a tributary to rebel (%)")
    conquest_conversion_chance: int = rule(45, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "On conquest the defeated converts to the victor's god (%)")
    tribute_conversion_chance: int = rule(20, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Under tribute the defeated converts to the victor's god (%)")
    exhaustion_victory_margin: int = rule(
        2, 1, 50, RuleGroup.WAR_AND_DIPLOMACY, "Minimum score advantage to count as the victor in an exhaustion peace (below it, white peace)"
    )
    duel_chance: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Heroes engage in a duel during a battle (%)")
    duel_death_chance: int = rule(45, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A duel ends in death (%)")
    capture_chance: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A hero of the defeated side is captured (%)")
    four_battle_exhaustion_chance: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Exhaustion peace after four battles (%)")
    conquest_syncretism_pct: int = rule(35, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Share of conquest conversions that are syncretic (%)")
    tribute_revolt_chance: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A strengthened tributary rebels (%)")
    ransom_chance: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A wealthy homeland pays ransom (%)")
    execution_chance: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A blood enemy executes the captive (%)")
    captive_defection_chance: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Switching sides after long captivity (%)")
