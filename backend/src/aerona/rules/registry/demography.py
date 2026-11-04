from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.POPULATION_AND_GROWTH
S = RuleGroup.ECONOMY


@dataclass(frozen=True)
class CohortsRules:
    child_pct: int = rule(32, 0, 100, G, "Share of a new community's people who are children (%)")
    elder_pct: int = rule(10, 0, 100, G, "Share of a new community's people who are elders (%)")
    female_pct: int = rule(50, 0, 100, G, "Share of women among the people (%)")
    dormant_after_epochs: int = rule(6, 1, 1000, G, "Epochs a named mortal of low importance may stay uninvolved before falling dormant")
    dormant_importance: int = rule(40, 0, 1000, G, "Importance below which an uninvolved named mortal may fall dormant")
    named_mortal_soft_limit_per_world: int = rule(
        10000, 1, 10000000, G, "Named mortals in a world above which promotion from cohorts slows (it never deletes, merges or blocks births)"
    )
    promotion_chance: int = rule(30, 0, 100, G, "A notable cohort event raises one of its people as a named mortal (%)")
    promotion_over_limit_pct: int = rule(20, 0, 100, G, "Promotion chance kept once a world is over its soft limit of named mortals (%)")
    promotion_maimed_min: int = rule(100, 1, 1000000, G, "Maimed in one epoch that count as a mass maiming")
    promotion_famine_dead_min: int = rule(200, 1, 1000000, G, "Famine dead in one epoch that leave orphans worth a name")
    promotion_cap: int = rule(4, 0, 100, G, "Most named mortals raised from cohorts in an epoch")


@dataclass(frozen=True)
class DemographyRules:
    birth_pct_per_year: int = rule(9, 0, 100, G, "Children born a year per hundred adult women of full fertility, fed and healthy (%)")
    child_death_pct_per_year: int = rule(3, 0, 100, G, "Children who die in a year at a neutral health (%)")
    adult_death_pct_per_year: int = rule(1, 0, 100, G, "Adults who die in a year at a neutral health (%)")
    elder_death_pct_per_year: int = rule(8, 0, 100, G, "Elders who die in a year at a neutral health (%)")
    hunger_birth_pct: int = rule(60, 0, 100, G, "Births lost at the worst hunger (%)")
    hunger_death_pct: int = rule(150, 0, 1000, G, "Extra deaths at the worst hunger (%)")
    crowding_death_pct: int = rule(60, 0, 1000, G, "Extra deaths where a land holds more people than its capacity (%)")
    disease_death_pct: int = rule(80, 0, 1000, G, "Extra deaths at the heaviest disease load (%)")
    stress_birth_pct: int = rule(30, 0, 100, G, "Births lost at war or in deep unrest (%)")
    immortality_death_pct: int = rule(10, 0, 1000, G, "Deaths kept under the immortality law (%)")
    short_life_death_pct: int = rule(200, 0, 1000, G, "Deaths under the short-life law (%)")
    sampled_years: int = rule(5, 1, 100, G, "Years of births and deaths computed in an epoch (the rest are extrapolated)")


@dataclass(frozen=True)
class LabourRules:
    satisfaction_pct: int = rule(20, 0, 100, S, "Output gained by a content class and lost by a bitter one, at the extremes (%)")
    soldier_pct: int = rule(60, 0, 100, S, "Share of warriors who soldier rather than farm in peace (%)")
    price_pull_pct: int = rule(30, 0, 100, S, "How strongly dear goods pull workers into the trades that make them (%)")
    idle_outcast_pct: int = rule(70, 0, 100, S, "Share of outcasts who find no work (%)")
    slave_output_pct: int = rule(130, 0, 500, S, "Output of serfs and slaves in mines and fields compared with free workers (%)")


@dataclass(frozen=True)
class PeopleRules:
    maturity_years: int = rule(16, 1, 1000, G, "Years a child takes to come of age in a human-like people")
    adult_years: int = rule(40, 1, 10000, G, "Years of adult life in a human-like people")
    elder_years: int = rule(15, 1, 10000, G, "Years of old age in a human-like people")
    cohesion_base: int = rule(55, 0, 100, G, "Cohesion of a people with a single tongue and faith")
    cohesion_per_tongue: int = rule(10, 0, 100, G, "Cohesion lost per extra tongue spoken among the people")
    literacy_per_writing_level: int = rule(12, 0, 100, G, "Literacy gained per level of writing knowledge")
    urban_per_settlement: int = rule(8, 0, 100, G, "Urbanisation gained per settlement of the people")
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
    manumission_chance: int = rule(10, 0, 100, S, "A share of a community's serfs and slaves is freed in an epoch (%)")
    manumission_pct: int = rule(10, 0, 100, S, "Share of the bound freed when they are freed (%)")
    enslave_captives_pct: int = rule(60, 0, 100, S, "Share of a conquered community's captives bound where slavery is lawful (%)")
    slavery_cohesion_loss: int = rule(4, 0, 100, S, "Cohesion a slave-holding people loses each epoch")
    slavery_opinion_loss: int = rule(5, 0, 100, S, "Relation xenophile neighbours lose with a slave-holding people each epoch")
    slavery_revolt_pct: int = rule(30, 0, 300, S, "Revolt pressure added by the share of the bound (%)")
