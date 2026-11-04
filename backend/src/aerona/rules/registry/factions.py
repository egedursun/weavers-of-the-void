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
    act_chance: int = rule(60, 0, 100, RuleGroup.CIVILIZATION, "A faction acts on its agenda in an epoch (%)")
    act_cap: int = rule(40, 0, 1000, RuleGroup.CIVILIZATION, "Most faction acts in an epoch")
    dues_per_member: int = rule(2, 0, 1000, RuleGroup.CIVILIZATION, "Treasury a faction collects per member each epoch")
    wealth_dues: int = rule(1, 0, 1000, RuleGroup.CIVILIZATION, "Treasury per ten points of a faction's wealth each epoch")
    lobby_cost: int = rule(10, 0, 100000, RuleGroup.CIVILIZATION, "Treasury a lobbying campaign costs")
    lobby_influence: int = rule(5, 0, 100, RuleGroup.CIVILIZATION, "Influence over a realm a lobbying campaign wins")
    bribe_cost: int = rule(25, 0, 100000, RuleGroup.CIVILIZATION, "Treasury a bribe costs")
    bribe_opinion: int = rule(15, 0, 100, RuleGroup.CIVILIZATION, "Good memory a bribe leaves with an office holder")
    bribe_influence: int = rule(8, 0, 100, RuleGroup.CIVILIZATION, "Influence over a realm a bribe wins")
    strike_unrest: int = rule(8, 0, 100, RuleGroup.CIVILIZATION, "Unrest a guild strike causes in its city")
    strike_prosperity: int = rule(3, 0, 100, RuleGroup.CIVILIZATION, "Prosperity a guild strike costs its city")
    riot_order: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "Public order a riot destroys")
    fund_war_share_pct: int = rule(30, 0, 100, RuleGroup.CIVILIZATION, "Share of its treasury a faction gives to a war it favours (%)")
    recruit_members: int = rule(2, 0, 100, RuleGroup.CIVILIZATION, "Mortals a recruiting drive brings in")
    recruit_share: int = rule(2, 0, 100, RuleGroup.CIVILIZATION, "Share of its class a recruiting drive adds to a faction (%)")
    schism_cohesion: int = rule(25, 0, 100, RuleGroup.CIVILIZATION, "Cohesion below which a faction may split")
    schism_chance: int = rule(20, 0, 100, RuleGroup.CIVILIZATION, "A divided faction splits in an epoch (%)")
    cohesion_drift: int = rule(3, 0, 100, RuleGroup.CIVILIZATION, "Cohesion a faction loses each epoch its goals go unmet")
    progress_step: int = rule(15, 0, 100, RuleGroup.CIVILIZATION, "Progress a successful act adds to its goal")
    balance_pct: int = rule(30, 0, 100, RuleGroup.CIVILIZATION, "Weight of the factions' power balance in a realm's decisions (%)")
    reputation_step: int = rule(5, 0, 100, RuleGroup.CIVILIZATION, "Reputation a faction gains or loses for an act its people approve or abhor")
    band_members: int = rule(8, 1, 1000, RuleGroup.CIVILIZATION, "Members at which a band becomes a company")
    company_members: int = rule(20, 1, 1000, RuleGroup.CIVILIZATION, "Members at which a company becomes an organisation")
    network_influence: int = rule(3, 1, 100, RuleGroup.CIVILIZATION, "Realms influenced at which an organisation becomes a network")
    monopoly_price_pct: int = rule(140, 100, 500, RuleGroup.CIVILIZATION, "Price of a commodity under a guild monopoly (%)")
    monopoly_crime: int = rule(4, 0, 100, RuleGroup.CIVILIZATION, "Crime smuggling around a monopoly adds to its city")
    goal_cap: int = rule(3, 1, 20, RuleGroup.CIVILIZATION, "Most goals a faction pursues at once")
    craft_min_artisan_pct: int = rule(12, 0, 100, RuleGroup.CIVILIZATION, "Artisan share of a community that founds a craft guild (%)")
    noble_min_pct: int = rule(4, 0, 100, RuleGroup.CIVILIZATION, "Noble share of a community that founds a council of lords (%)")
    peasant_min_farmer_pct: int = rule(40, 0, 100, RuleGroup.CIVILIZATION, "Farmer share of a community that founds a peasant league (%)")
    peasant_bitter: int = rule(35, 0, 100, RuleGroup.CIVILIZATION, "Farmer satisfaction below which farmers band into a league")
    academy_min_scribe_pct: int = rule(4, 0, 100, RuleGroup.CIVILIZATION, "Scribe share of a community that founds an academy (%)")
    secret_unrest: int = rule(60, 0, 100, RuleGroup.CIVILIZATION, "Unrest at which a secret society forms")
    assassins_crime: int = rule(55, 0, 100, RuleGroup.CIVILIZATION, "Crime at which an assassins' guild forms")
    bandits_outcast_pct: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "Outcast share at which outlaws band together (%)")
    bandits_crime: int = rule(40, 0, 100, RuleGroup.CIVILIZATION, "Crime at which outlaws band together")
    mercenary_min_warrior_pct: int = rule(16, 0, 100, RuleGroup.CIVILIZATION, "Warrior share of a community at peace that founds a free company (%)")


@dataclass(frozen=True)
class IntrigueRules:
    assassinate_chance: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "An assassination attempt kills its mark (%)")
    assassinate_hp: int = rule(60, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Wounds an assassin deals")
    exposure_pct: int = rule(60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Chance a plot is exposed at no secrecy (%)")
    exposure_reputation: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Reputation a faction loses when its plot is exposed")
    coup_strength: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Faction strength a coup needs")
    coup_chance: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A coup by an armed faction with a claimant succeeds (%)")
    secret_base: int = rule(60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Secrecy of a newly founded secret society or assassins' guild")


@dataclass(frozen=True)
class MercenariesRules:
    pay: int = rule(20, 0, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Pay a mercenary company asks per epoch")
    hire_chance: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A realm at war hires an idle company in an epoch (%)")
    contract_epochs: int = rule(3, 1, 100, RuleGroup.WAR_AND_DIPLOMACY, "Epochs a condotta runs")
    loyalty_paid: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Loyalty a paid company gains each epoch")
    loyalty_unpaid: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Loyalty an unpaid company loses each epoch")
    defect_loyalty: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Loyalty below which an unpaid company defects")
    banditry_chance: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A defecting company turns bandit rather than changing sides (%)")


@dataclass(frozen=True)
class BanditryRules:
    raid_prosperity: int = rule(4, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Prosperity a bandit raid takes from a settlement")
    raid_loot: int = rule(15, 0, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Treasury a raid brings the band")
    smuggle_loot: int = rule(10, 0, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Treasury smuggling brings a band")
    smuggle_crime: int = rule(3, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Crime smuggling adds to the city it works")
    suppress_strength: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Strength a suppression campaign takes from outlawed bands")
    suppress_chance: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A realm marches against an outlawed band in its lands in an epoch (%)")
    destroy_strength: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Strength at which a suppressed band is broken")
    privateer_relation: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Relation a privateer's raids cost its charterer's enemies")
