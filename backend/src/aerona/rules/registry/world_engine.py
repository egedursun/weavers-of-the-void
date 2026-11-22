from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class WorldEngineRules:
    chronicle_fold_threshold: int = rule(
        3, 2, 100, RuleGroup.CHRONICLE, "Lines of one kind in one epoch from which the feed shows them as one group, every line still reachable"
    )
    raid_danger_divisor: int = rule(160, 10, 10000, RuleGroup.CREATURES, "Monster raid chance: danger / this number")
    raid_loss_divisor: int = rule(400, 10, 10000, RuleGroup.CREATURES, "Population lost in a raid: danger / this number")
    monster_top_pct: int = rule(80, 0, 100, RuleGroup.CREATURES, "Species counted as monsters: the world's top X% most dangerous")
    monster_min_danger: int = rule(40, 0, 100, RuleGroup.CREATURES, "Minimum danger to count as a monster")
    monster_always_danger: int = rule(55, 0, 100, RuleGroup.CREATURES, "A species at this danger is always a monster")
    hunt_chance: int = rule(30, 0, 100, RuleGroup.HEROES_AND_MORTALS, "A strong mortal hunts a monster in pursuit of renown (%)")
    hunt_chosen_chance: int = rule(50, 0, 100, RuleGroup.HEROES_AND_MORTALS, "A chosen mortal hunts a monster (%)")
    hunter_strength_agility: int = rule(90, 0, 200, RuleGroup.HEROES_AND_MORTALS, "Strength + agility total of a mortal counted as a hunter")
    curse_lift_chance: int = rule(12, 0, 100, RuleGroup.HEROES_AND_MORTALS, "A curse lifts on its own (%)")
    curse_hp_loss: int = rule(10, 0, 1000, RuleGroup.HEROES_AND_MORTALS, "HP lost each epoch by a cursed mortal (if it runs out the curse kills them; 0 off)")
    curse_magic_bonus_pct: int = rule(15, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Contribution of knowing magic to escaping a curse (%)")
    curse_medicine_bonus_pct: int = rule(10, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Contribution of knowing medicine to escaping a curse (%)")
    first_epoch_years_engine: int = rule(15, 0, 50, RuleGroup.HEROES_AND_MORTALS, "Years an engine-born mortal lives in the epoch of birth")
    first_epoch_years_son: int = rule(35, 0, 50, RuleGroup.HEROES_AND_MORTALS, "Years a son-created mortal lives in the epoch of creation")
    notable_lifespan_bonus: int = rule(15, 0, 500, RuleGroup.HEROES_AND_MORTALS, "Extra lifespan of notable mortals (years)")
    medicine_lifespan_bonus: int = rule(20, 0, 500, RuleGroup.HEROES_AND_MORTALS, "Extra lifespan in a region that knows medicine (years)")
    growth_min_pct: int = rule(3, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Minimum rate of population growth (%)")
    growth_fertility_divisor: int = rule(600, 10, 100000, RuleGroup.POPULATION_AND_GROWTH, "Fertility contribution to growth: fertility / this number")
    growth_prosperity_divisor: int = rule(
        400, 10, 100000, RuleGroup.POPULATION_AND_GROWTH, "Prosperity contribution to growth in a city: (prosperity \u2212 40) / this number"
    )
    growth_agriculture_pct: int = rule(140, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Growth multiplier for those who know agriculture (%)")
    growth_max_pct: int = rule(400, 0, 10000, RuleGroup.POPULATION_AND_GROWTH, "Maximum growth in one epoch (%)")
    shrink_max_pct: int = rule(90, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Maximum shrinkage in one epoch (%)")
    carrying_capacity: int = rule(500000, 100, 1000000000, RuleGroup.POPULATION_AND_GROWTH, "Base carrying capacity of a region (people)")
    capacity_agriculture_pct: int = rule(
        120, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Contribution of agriculture to capacity (by share of those knowing agriculture, %)"
    )
    capacity_crowded_cap_pct: int = rule(150, 100, 1000, RuleGroup.POPULATION_AND_GROWTH, "Capacity cap of a region with many communities (%)")
    cult_growth_base_pct: int = rule(5, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Base of cult growth (%)")
    cult_growth_influence_divisor: int = rule(
        400, 10, 100000, RuleGroup.POPULATION_AND_GROWTH, "Influence contribution to cult growth: influence / this number"
    )
    cult_growth_charisma_divisor: int = rule(
        500, 10, 100000, RuleGroup.POPULATION_AND_GROWTH, "Patron charisma contribution to cult growth: charisma / this number"
    )
    god_grudge_spill_chance: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "The gods' grudge seeps into mortals (% per pair)")
    cursed_item_contagion_chance: int = rule(25, 0, 100, RuleGroup.HEROES_AND_MORTALS, "A cursed item infects its owner (%)")
    magic_storm_chance: int = rule(8, 0, 100, RuleGroup.COSMIC_HORROR, "Magic storm in a magic-dense region (%)")
    magic_storm_curse_chance: int = rule(30, 0, 100, RuleGroup.COSMIC_HORROR, "An item is cursed in a magic storm (%)")
    famine_migration_chance: int = rule(25, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Famine migration (%)")
    spirit_haunt_chance: int = rule(30, 0, 100, RuleGroup.THE_BEYOND, "A restless spirit haunts a settlement (%)")
    sorcerer_act_chance: int = rule(30, 0, 100, RuleGroup.HEROES_AND_MORTALS, "A sorcerer casts magic this epoch (%)")
    sorcerer_curse_chance: int = rule(50, 0, 100, RuleGroup.HEROES_AND_MORTALS, "A sorcerer curses an enemy (otherwise protects) (%)")
    birth_chance: int = rule(30, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Chance in each spacing of births that lovers or married mortals have a child (%)")
    dialect_split_chance: int = rule(15, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Dialect divergence in an isolated settlement (%)")
    ghost_chance: int = rule(50, 0, 100, RuleGroup.THE_BEYOND, "If the dead return, the deceased becomes a ghost (%)")
    famous_spirit_chance: int = rule(30, 0, 100, RuleGroup.THE_BEYOND, "A famous dead person's spirit does not rest (%)")
    mourning_tradition_chance: int = rule(40, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Mourning tradition for a famous dead person (%)")
    seafaring_reach_hops: int = rule(
        6, 1, 100, RuleGroup.MORTAL_AGENTS, "Map regions away a seafaring community can still reach (unless the sea ban law holds)"
    )
