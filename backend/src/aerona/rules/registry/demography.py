from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

G = RuleGroup.POPULATION_AND_GROWTH
S = RuleGroup.ECONOMY


@dataclass(frozen=True)
class CohortsRules:
    child_pct: int = rule(32, 0, 100, G, "Share of a new community's people who are infants, children or youths (%)")
    elder_pct: int = rule(10, 0, 100, G, "Share of a new community's people who are elders (%)")
    bearer_pct: int = rule(50, 0, 100, G, "Share of those who bear young among a two-sexed people (%)")
    dormant_after_epochs: int = rule(6, 1, 1000, G, "Epochs a named mortal of low importance may stay uninvolved before falling dormant")
    dormant_importance: int = rule(40, 0, 1000, G, "Importance below which an uninvolved named mortal may fall dormant")
    named_mortal_soft_limit_per_world: int = rule(
        10000, 1, 10000000, G, "Named mortals in a world above which promotion from cohorts slows (it never deletes, merges or blocks births)"
    )
    promotion_chance: int = rule(30, 0, 100, G, "A notable cohort event raises one of its people as a named mortal (%)")
    promotion_over_limit_pct: int = rule(20, 0, 100, G, "Promotion chance kept once a world is over its soft limit of named mortals (%)")
    promotion_maimed_min: int = rule(100, 1, 1000000, G, "Maimed in one epoch that count as a mass maiming")
    promotion_famine_dead_min: int = rule(200, 1, 1000000, G, "Famine dead in one epoch that leave orphans worth a name")
    named_famine_pct: int = rule(20, 0, 100, G, "Chance that a famine heavy enough to leave orphans also takes the frailest named mortal of the town (%)")
    promotion_cap: int = rule(4, 0, 10000, G, "Most named mortals raised from cohorts in one world in an epoch, before its people add more")
    promotion_people_per_extra: int = rule(
        50000, 0, 100000000, G, "People of a world that let one more named mortal rise from its cohorts in an epoch (0 for none)"
    )
    promotion_injury_severity: int = rule(4, 1, 5, G, "Severity of the matching wound a mortal raised from a mass maiming bears")
    promotion_orphan_intensity: int = rule(70, 0, 100, G, "Weight of the famine memory a mortal raised as a famine orphan carries")
    ancient_pct: int = rule(2, 0, 50, G, "Share of a community that has lived past old age when its ages are not yet counted (%)")


@dataclass(frozen=True)
class DemographyRules:
    birth_pct_per_year: int = rule(9, 0, 100, G, "Young born a year per hundred grown bearers of full fertility, fed and healthy (%)")
    child_death_pct_per_year: int = rule(3, 0, 100, G, "Children who die in a year at a neutral health (%)")
    adult_death_pct_per_year: int = rule(1, 0, 100, G, "Adults who die in a year at a neutral health (%)")
    infant_mortality_pct: int = rule(15, 0, 100, G, "Infants who die in a year at a neutral health, before care, hunger and sickness (%)")
    youth_levy_pct: int = rule(60, 0, 100, G, "How readily youths are drawn into levies and lost in war compared with adults (%)")
    orphan_care_need: int = rule(20, 0, 100, G, "Unrest a community bears at a full share of orphans left without the care of kin, faith or the realm")
    displaced_pressure: int = rule(10, 0, 100, G, "Unrest a community bears at a full share of the displaced pressing on it")
    orphan_emerge_pct: int = rule(5, 0, 100, G, "Added chance an orphan or one of the displaced steps out of the crowd as a named mortal (%)")
    displaced_settle_pct: int = rule(50, 0, 100, G, "Share of the displaced who settle among their hosts each epoch (%)")
    elder_death_pct_per_year: int = rule(8, 0, 100, G, "Elders who die in a year at a neutral health (%)")
    ancient_death_pct_per_year: int = rule(20, 0, 100, G, "Those who have lived past old age who die in a year at a neutral health (%)")
    hunger_birth_pct: int = rule(60, 0, 100, G, "Births lost at the worst hunger (%)")
    hunger_death_pct: int = rule(150, 0, 1000, G, "Extra deaths at the worst hunger (%)")
    crowding_death_pct: int = rule(60, 0, 1000, G, "Extra deaths where a land holds more people than its capacity (%)")
    disease_death_pct: int = rule(80, 0, 1000, G, "Extra deaths at the heaviest disease load (%)")
    endemic_baseline: int = rule(45, 0, 100, G, "Disease load the ordinary death rates already carry; only the load above it adds deaths")
    stress_birth_pct: int = rule(30, 0, 100, G, "Births lost at war or in deep unrest (%)")
    immortality_death_pct: int = rule(10, 0, 1000, G, "Deaths kept under the immortality law (%)")
    short_life_death_pct: int = rule(200, 0, 1000, G, "Deaths under the short-life law (%)")


@dataclass(frozen=True)
class LabourRules(Spanned):
    satisfaction_pct: int = rule(20, 0, 100, S, "Output gained by a content class and lost by a bitter one, at the extremes (%)")
    transport_base_share: int = rule(30, 0, 100, S, "Share of traders who carry goods and people rather than buy and sell (%)")
    administration_base_share: int = rule(40, 0, 100, S, "Share of officials and professionals who keep the books and offices of the realm (%)")
    gathering_base_share: int = rule(10, 0, 100, S, "Share of those who work the land who gather from the wild instead (%)")
    industry_base_share: int = rule(25, 0, 100, S, "Share of workers' craft done in works and factories (%)")
    arts_base_share: int = rule(15, 0, 100, S, "Share of artisans' craft given to performance and the making of art (%)")
    clerk_admin_pct: int = rule(40, 0, 200, S, "Administration a town gains at a full share of its people keeping its offices (%)")
    artist_prestige: int = rule(30, 0, 100, S, "Prestige a town gains at a full share of its people working at the arts")
    soldier_pct: int = rule(60, 0, 100, S, "Share of warriors who soldier rather than farm in peace (%)")
    price_pull_pct: int = rule(30, 0, 100, S, "How strongly dear goods pull workers into the trades that make them (%)")
    law_pin_pct: int = rule(70, 0, 100, S, "Share of the workers of a trade that a statute, a caste or a guild right keeps in it against every other pull (%)")
    skill_pull_pct: int = rule(30, 0, 100, S, "How strongly a people's knowledge pulls workers toward the trades it fits, where law allows (%)")
    idle_outcast_pct: int = rule(70, 0, 100, S, "Share of outcasts who find no work (%)")
    slave_output_pct: int = rule(130, 0, 500, S, "Output of serfs and slaves in mines and fields compared with free workers (%)")
    workshop_workers_per_level: int = rule(40, 0, 100000, S, "Workers each level of a workshop draws into its trade in a small community")
    workshop_workers_per_thousand: int = rule(8, 0, 1000, S, "Further workers each level of a workshop draws per thousand people of its community")
    resource_workers: int = rule(
        60, 0, 100000, S, "Workers a worked mine, quarry, fishery or forest of middling richness (50) draws into its trade; richer ones draw more"
    )
    resource_workers_per_thousand: int = rule(15, 0, 1000, S, "Further workers each worked deposit draws per thousand people of its community")
    corvee_unrest: int = rule(8, 0, 100, S, "Unrest a corvee of the whole people raises in a settlement each epoch")
    corvee_satisfaction: int = rule(15, 0, 100, S, "Contentment farmers and serfs lose under a corvee of the whole people")
    fund_per_member: int = rule(2, 0, 50, S, "Coin each member of a worker body pays into its strike fund in an epoch")
    strike_output_loss_pct: int = rule(80, 0, 100, S, "Share of a trade's output a full strike of its workers stops (%)")
    lockout_cost_pct: int = rule(30, 0, 100, S, "Share of the wages it holds back that a hirer loses each epoch it locks its workers out (%)")
    substitute_strength_pct: int = rule(
        50, 0, 100, S, "Strength a hirer gains in bargaining when bound workers, made minds or constructs could do the work (%)"
    )
    spread_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a won dispute stirs the same trade in another town (%)")
    banned_body_prosecution_pct: int = rule(20, 0, 100, S, "Chance in an epoch that a banned worker body is prosecuted (%)")
    found_chance_pct: int = rule(8, 0, 100, S, "Chance in an epoch that the bitter workers of a trade found a worker body (%)")
    found_min_workers: int = rule(80, 1, 1000000, S, "Workers a trade must hold in a town before they found a worker body")
    strike_pay: int = rule(1, 0, 100, S, "Coin a worker body's fund pays each worker out in an epoch")
    wage_per_strength: int = rule(50, 0, 200, S, "How far wages move from the customary for each hundred points of difference in strength (%)")
    dispute_gap: int = rule(15, 0, 100, S, "Strength a hirer must hold over a worker body before the body takes to a dispute rather than agree")
    lockout_gap: int = rule(30, 0, 100, S, "Strength a hirer must hold over a worker body before it locks the workers out")
    lockout_chance_pct: int = rule(20, 0, 100, S, "Chance in an epoch that a much stronger hirer locks out a body that bargains with it (%)")
    contract_term_years: int = span(5, 1, 500, S, "Years a labour contract runs before it is bargained again")
    dispute_max_years: int = span(2, 1, 500, S, "Years after which a labour dispute that neither side has won is settled")
    satisfaction_per_term: int = rule(5, 0, 100, S, "Contentment the workers of a trade gain or lose when their contract is good or bad, at the extremes")
    solidarity_won: int = rule(15, 0, 100, S, "Solidarity a worker body gains when it wins a dispute and loses when it loses one")
    solidarity_drift_pct: int = rule(
        40, 0, 100, S, "Share of the way a worker body's solidarity moves each epoch toward the discontent of the workers it covers (%)"
    )
    strikebreaker_substitutes_pct: int = rule(40, 0, 100, S, "Share of substitute workers above which a hirer brings in strikebreakers (%)")
    strikebreaker_hits: int = rule(2, 0, 20, S, "Members of a worker body hurt when strikebreakers are brought in")
    prosecution_fund_pct: int = rule(50, 0, 100, S, "Share of a banned body's fund seized when it is prosecuted (%)")
    cooperative_payout_pct: int = rule(
        30, 0, 100, S, "Share of a cooperative's treasury above its reserve paid out to its workers by their work in an epoch (%)"
    )

    @property
    def contract_term_epochs(self) -> int:
        return self.epochs(self.contract_term_years)

    @property
    def dispute_max_epochs(self) -> int:
        return self.epochs(self.dispute_max_years)


@dataclass(frozen=True)
class PeopleRules:
    maturity_years: int = rule(16, 1, 1000, G, "Years a child takes to come of age in a human-like people")
    adult_years: int = rule(40, 1, 10000, G, "Years of adult life in a human-like people")
    elder_years: int = rule(15, 1, 10000, G, "Years of old age in a human-like people")
    cohesion_base: int = rule(55, 0, 100, G, "Cohesion of a people with a single tongue and faith")
    cohesion_per_tongue: int = rule(10, 0, 100, G, "Cohesion lost per extra tongue spoken among the people")
    literacy_per_writing_level: int = rule(12, 0, 100, G, "Literacy gained per level of writing knowledge")
    urban_per_settlement: int = rule(100, 0, 100, G, "Share of the people's folk living in its settlements that counts as its urbanisation (% of that share)")
    assimilation_distance: int = rule(20, 0, 300, G, "Value distance below which a people of low cohesion assimilates into a neighbour sharing its tongue")
    assimilation_cohesion: int = rule(40, 0, 100, G, "Cohesion below which a people may assimilate")
    ethnogenesis_distance: int = rule(35, 0, 300, G, "Value distance from its parent people at which a settlement becomes a people of its own")


@dataclass(frozen=True)
class MobilityRules:
    inequality_crime_pct: int = rule(
        40, 0, 300, S, "Crime and revolt pressure from the widest gap between classes, before a hierarchical culture forgives it (%)"
    )
    hierarchy_tolerance_pct: int = rule(60, 0, 100, S, "Share of inequality a fully hierarchical culture tolerates (%)")
    desertion_pct: int = rule(8, 0, 100, S, "Soldiers who desert in an epoch when the warrior class is bitter (%)")
    bitter_satisfaction: int = rule(30, 0, 100, S, "Satisfaction below which a class counts as bitter")
    ennoble_chance: int = rule(40, 0, 100, S, "A war hero is raised among the nobles (%)")
    ruin_chance: int = rule(30, 0, 100, S, "A merchant of a bankrupt guild falls among the outcasts (%)")
    enrich_threshold: int = rule(70, 0, 100, S, "Wealth at which a commoner rises among the merchants where the culture lets wealth buy rank")
    enrich_hierarchy_max: int = rule(60, -100, 100, S, "Hierarchy above which a culture refuses to let wealth alone raise anyone's rank")
    manumission_chance: int = rule(10, 0, 100, S, "A share of a community's serfs and slaves is freed in an epoch (%)")
    manumission_pct: int = rule(10, 0, 100, S, "Share of the bound freed when they are freed (%)")
    enslave_captives_pct: int = rule(60, 0, 100, S, "Share of a conquered community's captives bound where slavery is lawful (%)")
    slavery_cohesion_loss: int = rule(4, 0, 100, S, "Cohesion a slave-holding people loses each epoch")
    slavery_opinion_loss: int = rule(5, 0, 100, S, "Relation xenophile neighbours lose with a slave-holding people each epoch")
    slavery_revolt_pct: int = rule(30, 0, 300, S, "Revolt pressure added by the share of the bound (%)")
    wealth_drift_pct: int = rule(25, 0, 100, S, "Share of the gap to its earned wealth a class closes each epoch (%)")
    wealth_per_supply_pct: int = rule(50, 0, 1000, S, "Wealth a community counts per point of its food, ore and goods supply gauges (%)")
    ennobled_memory: int = rule(25, 0, 100, S, "Gratitude an ennobled hero holds toward the people that raised them")
    enslaved_memory: int = rule(30, 0, 100, S, "Grievance a people holds toward those that enslaved its captured kin")
    freed_memory: int = rule(20, 0, 100, S, "Gratitude toward those that freed one's kin")
    ruined_memory: int = rule(30, 0, 100, S, "Grievance a ruined merchant holds toward the guild that failed")
