from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span


@dataclass(frozen=True)
class FactionsRules:
    faction_cap: int = rule(1, 0, 1000, RuleGroup.CIVILIZATION, "Base of the most factions founded spontaneously per epoch, grown by the number of communities")
    faction_cap_community_divisor: int = rule(
        4, 0, 1000, RuleGroup.CIVILIZATION, "Communities per extra faction founded spontaneously in an epoch (0: the cap stays at its base)"
    )
    faction_chance: int = rule(15, 0, 100, RuleGroup.CIVILIZATION, "A faction is founded within a community (%)")
    revolt_disband_chance: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "An uprising whose war ended disbands (%)")
    guild_min_merchant_pct: int = rule(11, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum merchant share of a community that founds a guild (%)")
    engineers_min_professional_pct: int = rule(
        5,
        0,
        100,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Minimum share of professionals of a community that knows engines or machine tools to found a society of engineers (%)",
    )
    guild_min_prosperity: int = rule(45, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum prosperity of a community that founds a guild")
    guild_strength: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base strength of a merchant guild")
    guild_wealth: int = rule(55, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base wealth of a merchant guild")
    guild_sway: int = rule(45, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base sway of a merchant guild")
    council_min_priest_pct: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum priest share of a community that founds a priests' council (%)")
    council_strength: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base strength of a priests' council")
    council_wealth: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base wealth of a priests' council")
    council_sway: int = rule(55, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base sway of a priests' council")
    order_min_warrior_pct: int = rule(14, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum warrior share of a community that founds a warrior order (%)")
    order_at_war_min_warrior_pct: int = rule(11, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum warrior share for a community at war (%)")
    order_strength: int = rule(55, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base strength of a warrior order")
    order_wealth: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base wealth of a warrior order")
    order_sway: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base sway of a warrior order")
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
    act_cap: int = rule(40, 0, 100000, RuleGroup.CIVILIZATION, "Base of the most faction acts in an epoch, grown by the number of factions")
    act_cap_faction_divisor: int = rule(1, 0, 1000, RuleGroup.CIVILIZATION, "Factions per extra faction act in an epoch (0: the cap stays at its base)")
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
    monopoly_price_pct: int = rule(140, 100, 500, RuleGroup.CIVILIZATION, "Price of a commodity under an association's monopoly (%)")
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
    found_renown: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "Renown a mortal needs to found a faction in their town")
    found_cost: int = rule(5, 0, 100, RuleGroup.CIVILIZATION, "Wealth a mortal spends to found a faction")


@dataclass(frozen=True)
class IntrigueRules(Spanned):
    assassinate_chance: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "An assassination attempt kills its mark (%)")
    assassinate_hp: int = rule(60, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Wounds an assassin deals")
    exposure_pct: int = rule(60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Chance a plot is exposed at no secrecy (%)")
    exposure_reputation: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Reputation a faction loses when its plot is exposed")
    coup_strength: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Faction strength a coup needs")
    coup_chance: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A coup by an armed faction with a claimant succeeds (%)")
    secret_base: int = rule(60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Secrecy of a newly founded secret society or assassins' guild")
    strong_at: int = rule(60, 0, 100, RuleGroup.REPUTATION, "Severity from which knowing a secret gives a strong hook that is not spent on use")
    expose_infamy_pct: int = rule(40, 0, 200, RuleGroup.REPUTATION, "Share of a secret's severity its holder gains as infamy when it comes out (%)")
    gossip_pct: int = rule(25, 0, 100, RuleGroup.REPUTATION, "Chance a gossip passes on a secret the gossiper knows about someone else (%)")
    confide_pct: int = rule(30, 0, 100, RuleGroup.REPUTATION, "Chance a mortal confides one of their own secrets to a close friend or lover (%)")
    spy_learn_pct: int = rule(20, 0, 100, RuleGroup.REPUTATION, "Chance each epoch a spy network learns a secret of someone it watches (%)")
    likeness_notice: int = rule(70, 0, 100, RuleGroup.REPUTATION, "Likeness to a hidden true parent from which kin may notice it")
    likeness_notice_pct: int = rule(10, 0, 100, RuleGroup.REPUTATION, "Chance each epoch kin notice a child's likeness to a hidden true parent (%)")
    favour_decay_pct: int = rule(10, 0, 100, RuleGroup.REPUTATION, "Share of a favour owed that fades each epoch it is not called (%)")
    weak_reciprocity_pct: int = rule(
        50, 0, 400, RuleGroup.REPUTATION, "How much faster favours fade where the debtor holds friendship of little worth, at its lowest (%)"
    )
    inherited_from: int = rule(30, -100, 100, RuleGroup.REPUTATION, "Family value from which the kin of a dead debtor take on the favours the debtor owed")
    obsolete_pct: int = rule(
        25, 0, 100, RuleGroup.REPUTATION, "Share of its severity a secret loses each epoch once its subject is dead or it is already known to all (%)"
    )
    debt_secret_at: int = rule(100, 0, 10000, RuleGroup.REPUTATION, "Debt from which a noble household hides what it owes")
    coward_anxiety: int = rule(30, -100, 100, RuleGroup.REPUTATION, "Anxiety from which a beaten commander may have fled the field in secret")
    coward_pct: int = rule(30, 0, 100, RuleGroup.REPUTATION, "Chance an anxious beaten commander hides that they fled (%)")
    hook_comply_pct: int = rule(
        90, 0, 100, RuleGroup.REPUTATION, "Chance a target complies when a weak hook is used on them; a strong hook always forces compliance (%)"
    )
    support_wealth: int = rule(10, 0, 100, RuleGroup.REPUTATION, "Wealth a mortal pressed for support hands over")
    favour_trust: int = rule(10, 0, 100, RuleGroup.REPUTATION, "Friendship an honoured favour brings")
    favour_refusal: int = rule(15, 0, 100, RuleGroup.REPUTATION, "Friendship and honour a refused favour costs")
    gift_favour: int = rule(10, 0, 100, RuleGroup.REPUTATION, "Magnitude of the favour a gift earns")
    rescue_favour: int = rule(40, 0, 100, RuleGroup.REPUTATION, "Magnitude of the favour a rescue earns")
    succession_favour: int = rule(30, 0, 100, RuleGroup.REPUTATION, "Magnitude of the favour an heir owes the ruler who named them")
    scheme_favour: int = rule(15, 0, 100, RuleGroup.REPUTATION, "Magnitude of the favour a schemer owes each agent of a scheme that succeeded")
    war_favour: int = rule(30, 0, 100, RuleGroup.REPUTATION, "Magnitude of the favour joining a war earns")
    identity_slip: int = rule(4, 0, 50, RuleGroup.REPUTATION, "Exposure a false identity gains each epoch for a mortal of little caution")
    identity_look: int = rule(3, 0, 50, RuleGroup.REPUTATION, "Exposure a false identity gains each epoch for every ten points of recognisability")
    identity_investigation: int = rule(40, 0, 100, RuleGroup.REPUTATION, "Exposure a false identity gains when an investigation names its wearer (%)")
    scheme_cap: int = rule(
        4, 0, 10000, RuleGroup.REPUTATION, "Base of the most new schemes the world's mortals begin each epoch, grown by the number of living mortals"
    )
    scheme_cap_mortal_divisor: int = rule(20, 0, 100000, RuleGroup.REPUTATION, "Living mortals per extra new scheme in an epoch (0: the cap stays at its base)")
    scheme_ambition_pct: int = rule(8, 0, 100, RuleGroup.REPUTATION, "Chance each epoch an ambitious or cruel mortal with a rival begins a scheme (%)")
    recruit_years: int = span(1, 0, 250, RuleGroup.REPUTATION, "Years a scheme spends recruiting before it prepares")
    agent_power: int = rule(10, 0, 100, RuleGroup.REPUTATION, "Power each agent adds to a scheme for every ten points of intrigue skill")
    owner_power: int = rule(15, 0, 100, RuleGroup.REPUTATION, "Power the scheme's owner adds for every ten points of intrigue skill")
    defence_spymaster: int = rule(20, 0, 100, RuleGroup.REPUTATION, "Defence a target's spymaster adds for every ten points of intrigue skill")
    defence_intuition_pct: int = rule(50, 0, 200, RuleGroup.REPUTATION, "How much the target's intuition adds to its defence (%)")
    discovery_pct: int = rule(15, 0, 100, RuleGroup.REPUTATION, "Chance each epoch a scheme is discovered at full counter-intelligence and no secrecy (%)")
    agent_wage: int = rule(15, 0, 1000, RuleGroup.REPUTATION, "Wealth a schemer pays each agent hired when friends, hooks and favours fall short")
    defence_bodyguard: int = rule(2, 0, 20, RuleGroup.REPUTATION, "Defence a ruler's court champion adds against schemes for every ten points of strength")
    cover_patience_pct: int = rule(60, 0, 100, RuleGroup.REPUTATION, "How much a skilled schemer waits for night, fog, crowds or panic before striking (%)")
    agent_exposure_pct: int = rule(
        50, 0, 100, RuleGroup.REPUTATION, "Share of a discovered scheme's weight its agents bear in the target's memory and in infamy (%)"
    )
    night_fog_pct: int = rule(20, 0, 100, RuleGroup.REPUTATION, "How much fog or a winter night raises a scheme's success and lowers its witnesses (%)")
    storm_pct: int = rule(15, 0, 100, RuleGroup.REPUTATION, "How much a storm raises a scheme's success by cutting pursuit (%)")
    crowd_pct: int = rule(10, 0, 100, RuleGroup.REPUTATION, "How much a festival raises a scheme's success while adding witnesses (%)")
    panic_pct: int = rule(15, 0, 100, RuleGroup.REPUTATION, "How much a plague panic or a siege raises a scheme's success (%)")
    true_name_chance_pct: int = rule(10, 0, 100, RuleGroup.REPUTATION, "Share of notable mortals, beasts, places and artifacts that carry a true name (%)")
    true_name_power_pct: int = rule(50, 0, 200, RuleGroup.REPUTATION, "How much knowing a true name strengthens a binding rite against its bearer (%)")
    exile_mask_pct: int = rule(40, 0, 100, RuleGroup.REPUTATION, "Chance an exile takes a new name to live under (%)")
    deceive_pct: int = rule(
        15, 0, 100, RuleGroup.REPUTATION, "Chance each epoch a deep spy network plants a false report of its owner's defences in its target (%)"
    )
    true_name_ward_pct: int = rule(40, 0, 100, RuleGroup.REPUTATION, "How much knowing a caster's true name shields its bearer from the caster's rites (%)")
    rename_known_at: int = rule(3, 1, 50, RuleGroup.REPUTATION, "Others who must know a true name before its bearer seeks a new one")
    rename_essence: int = rule(30, 0, 1000, RuleGroup.REPUTATION, "Essence a son spends to be reborn under a new true name")
    rename_initiation_pct: int = rule(
        20, 0, 100, RuleGroup.REPUTATION, "Chance each epoch a mortal or spirit whose true name is widely known takes a new one through initiation (%)"
    )
    research_name_pct: int = rule(5, 0, 100, RuleGroup.REPUTATION, "Chance each epoch a scholar of old tongues learns a true name in their land (%)")
    confide_name_pct: int = rule(
        3, 0, 100, RuleGroup.REPUTATION, "Chance each epoch a mortal confides their true name to a spouse, lover or intimate friend (%)"
    )

    @property
    def recruit_epochs(self) -> int:
        return self.epochs(self.recruit_years)


@dataclass(frozen=True)
class MercenariesRules(Spanned):
    pay: int = rule(
        20, 0, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Pay a mercenary company asks per epoch for each of its members (at least once for a company of none)"
    )
    hire_chance: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A realm at war hires an idle company in an epoch (%)")
    contract_years: int = span(3, 1, 2500, RuleGroup.WAR_AND_DIPLOMACY, "Years a condotta runs")
    loyalty_paid: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Loyalty a paid company gains each epoch")
    loyalty_unpaid: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Loyalty an unpaid company loses each epoch")
    defect_loyalty: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Loyalty below which an unpaid company defects")
    banditry_chance: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A defecting company turns bandit rather than changing sides (%)")

    @property
    def contract_epochs(self) -> int:
        return self.epochs(self.contract_years)


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
