from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class DeepWorldRules:
    notable_min_population: int = rule(800, 0, 1000000, RuleGroup.HEROES_AND_MORTALS, "Minimum population of a community producing a notable mortal")
    notable_chance: int = rule(45, 0, 100, RuleGroup.HEROES_AND_MORTALS, "A notable mortal arises from a populous community (base %)")
    notable_cap: int = rule(8, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Maximum notable mortals born per epoch")
    ruler_cap: int = rule(2, 0, 50, RuleGroup.HEROES_AND_MORTALS, "Maximum rulers taking the throne per epoch")
    ruler_min_population: int = rule(800, 0, 1000000, RuleGroup.HEROES_AND_MORTALS, "Minimum population of a community acquiring a ruler")
    ethnogenesis_min_population: int = rule(3000, 0, 10000000, RuleGroup.POPULATION_AND_GROWTH, "Minimum population of a settlement turning into a new people")
    ethnogenesis_min_age: int = rule(3, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Age required to turn into a new people (epochs)")
    spirits_per_place_cap: int = rule(3, 0, 30, RuleGroup.THE_BEYOND, "Maximum spirits roaming in one place")
    spirit_unrest_decay: int = rule(3, 0, 50, RuleGroup.THE_BEYOND, "Spirit's unrest decay per epoch")
    spirit_rest_threshold: int = rule(40, 0, 100, RuleGroup.THE_BEYOND, "A spirit with unrest below this may come to rest")
    cult_population_share_pct: int = rule(20, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Cap on cult followers: percentage of the region's population")
    young_world_epochs: int = rule(6, 0, 50, RuleGroup.COSMIC_HORROR, "Young world duration (epochs; leakage growth is halved)")
    first_village_population: int = rule(600, 50, 100000, RuleGroup.POPULATION_AND_GROWTH, "Population at which a people founds its first homeland")
    extra_village_population: int = rule(1500, 100, 1000000, RuleGroup.POPULATION_AND_GROWTH, "Population at which a people founds an additional village")
    village_min_population: int = rule(150, 10, 10000, RuleGroup.POPULATION_AND_GROWTH, "Minimum population of a new village")
    village_people_remainder: int = rule(
        300, 10, 100000, RuleGroup.POPULATION_AND_GROWTH, "Minimum population remaining in the people after founding a village"
    )
    people_per_village: int = rule(15000, 1000, 1000000, RuleGroup.POPULATION_AND_GROWTH, "One village per this many people in the region")
    ruin_population_threshold: int = rule(60, 0, 10000, RuleGroup.POPULATION_AND_GROWTH, "A settlement below this population is abandoned")
    ruin_grace_epochs: int = rule(2, 0, 20, RuleGroup.POPULATION_AND_GROWTH, "Epochs a new settlement takes root without being abandoned")
    structure_cap: int = rule(2, 0, 20, RuleGroup.CIVILIZATION, "Maximum structures the engine builds per epoch (base; grows with the community count)")
    structure_cap_community_divisor: int = rule(60, 0, 100000, RuleGroup.CIVILIZATION, "Structure cap grows by 1 for every this many communities (0: fixed)")
    structure_min_prosperity: int = rule(50, 0, 100, RuleGroup.CIVILIZATION, "Prosperity required to build a structure")
    splendor_gain: int = rule(2, 0, 50, RuleGroup.CIVILIZATION, "Splendor per epoch to the structure of a prosperous owner")
    golden_age_prosperity: int = rule(50, 0, 100, RuleGroup.APOCALYPSE, "Average prosperity required for a golden age")
    golden_age_peace_epochs: int = rule(4, 0, 50, RuleGroup.APOCALYPSE, "Epochs that must pass without war for a golden age")
    era_turn_interval: int = rule(10, 1, 1000, RuleGroup.APOCALYPSE, "Era turning every this many epochs")
    era_turn_apocalypse_push: int = rule(5, 0, 100, RuleGroup.APOCALYPSE, "Apocalypse push-back at an era turning")
    world_age_step: int = rule(25, 1, 1000, RuleGroup.APOCALYPSE, "World aging threshold (epochs)")
    refugee_share_pct: int = rule(8, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Population share of refugees (%)")
    famine_migration_share_pct: int = rule(15, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Population share of famine migration (%)")
    ruler_chance: int = rule(50, 0, 100, RuleGroup.HEROES_AND_MORTALS, "A ruler takes over a leaderless community (%)")
    ethnogenesis_chance: int = rule(20, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "An isolated settlement turns into a new people (%)")
    sapience_chance: int = rule(12, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "An intelligent species turns into a people (%)")
    script_chance: int = rule(50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A language whose speakers know writing gains a script (%)")
    manifestation_chance: int = rule(10, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A widespread legend becomes real (%)")
    legendization_chance: int = rule(25, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "An old violent event turns into a legend (%)")
    fairy_tale_chance: int = rule(15, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "An old legend turns into a fairy tale (%)")
    native_people_chance: int = rule(20, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "A native people appears on a world without a people (%)")
    native_species_chance: int = rule(25, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "A living species appears on a world without species (%)")
    new_people_worship_creator_chance: int = rule(
        50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A new godless people worships the Creator (otherwise seeks a god) (%)"
    )
    refugee_chance: int = rule(40, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Refugee migration after war or disaster (%)")
    spirit_rest_chance: int = rule(30, 0, 100, RuleGroup.THE_BEYOND, "A calm spirit comes to rest (%)")
    spirit_passage_chance: int = rule(12, 0, 100, RuleGroup.THE_BEYOND, "A spirit passes to the land of the dead (%)")
    structure_chance: int = rule(25, 0, 100, RuleGroup.CIVILIZATION, "A prosperous city builds a structure (%)")
