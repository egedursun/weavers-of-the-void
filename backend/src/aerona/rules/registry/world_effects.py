from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class WorldEffectsRules:
    afterdeath_cap: int = rule(2, 0, 50, RuleGroup.THE_BEYOND, "Maximum mourning traditions or spirits born from deaths per epoch (each)")
    afterdeath_cap_community_divisor: int = rule(
        10, 0, 100000, RuleGroup.THE_BEYOND, "Mourning tradition and spirit cap grows by 1 for every this many communities (0: fixed)"
    )
    god_grudge_cap: int = rule(1, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Maximum new hostilities born from god grudges per epoch (base)")
    god_grudge_cap_community_divisor: int = rule(
        20, 0, 100000, RuleGroup.WAR_AND_DIPLOMACY, "God grudge hostility cap grows by 1 for every this many communities (0: fixed)"
    )
    god_grudge_distance: int = rule(3, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Maximum map distance of communities a grudge can seep between (steps)")
    god_grudge_relation: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "For a grudge, the patron gods' relation must be at most minus this")
    raid_distance: int = rule(2, 0, 20, RuleGroup.CREATURES, "Maximum distance a monster can raid (steps)")
    raid_prosperity_loss: int = rule(6, 0, 100, RuleGroup.CREATURES, "Prosperity loss of a raided settlement")
    raid_defense_gain: int = rule(2, 0, 100, RuleGroup.CREATURES, "Wall (defense) increase of a settlement after a raid")
    unknown_stat: int = rule(30, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Default of an unrecorded defense, influence or value (and prosperity in uprisings)")
    unknown_prosperity: int = rule(50, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Default of unrecorded prosperity (raid, famine, haunting, law, growth)")
    unknown_fertility: int = rule(50, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Default of unrecorded fertility (drought, famine migration, growth)")
    unknown_breadth: int = rule(50, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Breadth in carrying capacity of a region with no recorded breadth")
    unknown_justice: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Justice of a law with no recorded justice")
    unknown_piety: int = rule(50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Piety in the godlessness calculation of a community with no recorded piety")
    raid_default_danger: int = rule(50, 0, 100, RuleGroup.CREATURES, "Danger in a raid of a monster with no recorded danger")
    raid_default_population: int = rule(100, 1, 1000000, RuleGroup.CREATURES, "Population in a raid of a settlement with no recorded population")
    hunt_distance: int = rule(3, 0, 20, RuleGroup.HEROES_AND_MORTALS, "Maximum distance of a monster a hero can hunt (steps)")
    prosperity_target: int = rule(
        50, 0, 100, RuleGroup.ECONOMY, "Equilibrium value prosperity is drawn to in the long run; trade and resource gains have diminishing returns above it"
    )
    prosperity_reversion_pct: int = rule(10, 0, 100, RuleGroup.ECONOMY, "Gap toward the equilibrium value that prosperity closes each epoch (%)")
    curse_population_kept_pct: int = rule(95, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Share of population and followers a cursed community keeps each epoch (%)")
    curse_stat_loss: int = rule(3, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Prosperity, fertility, strength and wealth a cursed entity loses each epoch")
    resource_regen: int = rule(4, 0, 100, RuleGroup.ECONOMY, "Per-epoch abundance regeneration of resources")
    item_curse_threshold: int = rule(50, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Minimum curse of an item that harms its owner")
    item_curse_hp_divisor: int = rule(
        5, 1, 1000, RuleGroup.HEROES_AND_MORTALS, "Harm a cursed item deals its owner, before their body takes it: curse / this number"
    )
    item_curse_stat_divisor: int = rule(20, 1, 1000, RuleGroup.HEROES_AND_MORTALS, "Prosperity and defense damage of a cursed item: curse / this number")
    magic_storm_min_magic: int = rule(70, 0, 100, RuleGroup.COSMIC_HORROR, "Minimum magic of a region where a magic storm can break out")
    magic_storm_might_gain: int = rule(5, 0, 100, RuleGroup.COSMIC_HORROR, "Might increase of resources and items in a magic storm")
    magic_storm_curse_gain: int = rule(10, 0, 100, RuleGroup.COSMIC_HORROR, "Curse increase of an item cursed in a magic storm")
    magic_storm_power: int = rule(5, 1, 12, RuleGroup.COSMIC_HORROR, "Power level of a magic storm event")
    magic_storm_severity_base: int = rule(40, 0, 100, RuleGroup.COSMIC_HORROR, "Base of magic storm severity")
    magic_storm_severity_die: int = rule(40, 1, 100, RuleGroup.COSMIC_HORROR, "Die added to magic storm severity (1\u2013X)")
    split_min_power: int = rule(2, 1, 12, RuleGroup.POPULATION_AND_GROWTH, "Minimum power level of a new entity that splits, migrates or converts")
    hungry_food: int = rule(15, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "A community with food below this counts as hungry")
    famine_migration_min_population: int = rule(
        1500, 0, 10000000, RuleGroup.POPULATION_AND_GROWTH, "Minimum population of a community able to make a famine migration"
    )
    famine_migration_cap: int = rule(1, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Maximum famine migrations per epoch (base)")
    famine_migration_cap_community_divisor: int = rule(
        10, 0, 100000, RuleGroup.POPULATION_AND_GROWTH, "Famine migration cap grows by 1 for every this many communities (0: fixed)"
    )
    famine_prosperity: int = rule(20, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "A community below this prosperity counts as in famine")
    famine_fertility_margin: int = rule(
        5, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "The destination region must be at least this much more fertile than the source"
    )
    migrant_prosperity: int = rule(30, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Starting prosperity of a migrant settlement")
    migrant_defense: int = rule(20, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Starting defense of a migrant settlement")
    migrant_piety: int = rule(55, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Starting piety of a migrant settlement")
    haunt_prosperity_loss: int = rule(6, 0, 100, RuleGroup.THE_BEYOND, "Prosperity loss of a settlement haunted by a spirit")
    haunt_unrest_drop: int = rule(5, 0, 100, RuleGroup.THE_BEYOND, "Decrease of the haunting spirit's unrest")
    law_just_avg_threshold: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "If the average justice of laws is above this, walls strengthen")
    law_just_defense_gain: int = rule(2, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch defense gain of a settlement with just laws")
    law_unjust_avg_threshold: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "If the average justice of laws is below this, prosperity drops")
    law_unjust_prosperity_loss: int = rule(2, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch prosperity loss of a settlement with unjust laws")
    sorcerer_min_intellect: int = rule(60, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Minimum intellect of a mortal who can be a sorcerer")
    sorcerer_protect_chance: int = rule(
        50, 0, 100, RuleGroup.HEROES_AND_MORTALS, "A sorcerer casts a protection (otherwise bounty) spell over their homeland (%)"
    )
    inheritance_default_stat: int = rule(40, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Default of an unrecorded mortal stat (inheritance and spirits)")
    inheritance_deviation: int = rule(10, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Deviation (\u00b1) of children's and heirs' stats from the parent")
    child_hp: int = rule(80, 1, 1000, RuleGroup.HEROES_AND_MORTALS, "HP of a newborn child")
    default_lifespan: int = rule(70, 1, 50000, RuleGroup.HEROES_AND_MORTALS, "Lifespan of a mortal with no recorded lifespan (years)")
    child_min_lifespan: int = rule(20, 1, 50000, RuleGroup.HEROES_AND_MORTALS, "Shortest lifespan of a newborn child (years)")
    dialect_min_settlement_age: int = rule(4, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Minimum settlement age for a dialect split (epochs)")
    dialect_cap: int = rule(1, 0, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Maximum dialect splits per epoch (base)")
    dialect_cap_settlement_divisor: int = rule(
        15, 0, 100000, RuleGroup.RELIGION_AND_LANGUAGE, "Dialect split cap grows by 1 for every this many settlements (0: fixed)"
    )
    dialect_power: int = rule(2, 1, 12, RuleGroup.RELIGION_AND_LANGUAGE, "Power level of a new dialect")
    dialect_spread: int = rule(15, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Spread of a new dialect")
    dialect_complexity: int = rule(40, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Complexity of a new dialect")
    dialect_sacredness: int = rule(10, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Sacredness of a new dialect")
    dialect_inherited_words: int = rule(5, 0, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Words passing from the parent language to the new dialect")
    magic_price_min_magic: int = rule(
        60, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Under the price-of-magic law, minimum magic of a people that pays the price"
    )
    magic_price_population_kept_pct: int = rule(
        95, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Under the price-of-magic law, population share a people keeps each epoch (%)"
    )
    architecture_defense_gain: int = rule(5, 0, 100, RuleGroup.CIVILIZATION, "Per-epoch wall gain of a settlement that knows architecture")
    notable_min_charisma: int = rule(70, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Minimum charisma of a mortal counted as notable (lives longer)")
    rejuvenate_years_left: int = rule(
        10,
        0,
        3000,
        RuleGroup.HEROES_AND_MORTALS,
        "A created mortal with only this many years left of their lifespan in the epoch of birth is rejuvenated (years)",
    )
    rejuvenate_age_min_pct: int = rule(20, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Age of a rejuvenated mortal: at least % of lifespan")
    rejuvenate_age_random_pct: int = rule(30, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Random share of lifespan added to a rejuvenated mortal's age (max %)")
    short_life_aging_mult: int = rule(2, 1, 20, RuleGroup.HEROES_AND_MORTALS, "Aging multiplier under the short-life law (times)")
    heir_hp: int = rule(80, 1, 1000, RuleGroup.HEROES_AND_MORTALS, "HP of an heir")
    heir_age_base: int = rule(16, 0, 200, RuleGroup.HEROES_AND_MORTALS, "Heir's age: base (years)")
    heir_age_die: int = rule(12, 1, 200, RuleGroup.HEROES_AND_MORTALS, "Die added to the heir's age (1\u2013X years)")
    heir_lifespan_deviation: int = rule(15, 0, 1000, RuleGroup.HEROES_AND_MORTALS, "Deviation (\u00b1 years) of the heir's lifespan from the deceased's")
    heir_min_lifespan: int = rule(45, 1, 50000, RuleGroup.HEROES_AND_MORTALS, "Shortest lifespan of an heir (years)")
    death_domain_essence: int = rule(2, 0, 100, RuleGroup.THE_BEYOND, "Essence a death-domain god gains on each death")
    death_domain_existence: int = rule(1, 0, 100, RuleGroup.THE_BEYOND, "Existence gain of a death-domain god on each death")
    famous_min_charisma: int = rule(60, 0, 100, RuleGroup.THE_BEYOND, "Minimum charisma of a deceased counted as famous")
    spirit_unrest_murdered: int = rule(70, 0, 100, RuleGroup.THE_BEYOND, "Base unrest of the spirit of a murdered famous person")
    spirit_unrest_natural: int = rule(40, 0, 100, RuleGroup.THE_BEYOND, "Base unrest of the spirit of a famous person who died naturally")
    spirit_unrest_die: int = rule(20, 1, 100, RuleGroup.THE_BEYOND, "Die added to the spirit's unrest (1\u2013X)")
    spirit_restless_threshold: int = rule(50, 0, 100, RuleGroup.THE_BEYOND, "A spirit with unrest above this counts as restless (below: ancestor spirit)")
    spirit_strength_divisor: int = rule(2, 1, 100, RuleGroup.THE_BEYOND, "Spirit's strength: deceased's strength / this number")
    spirit_strength_bonus: int = rule(20, 0, 100, RuleGroup.THE_BEYOND, "Added to the spirit's strength")
    mourning_power: int = rule(2, 1, 12, RuleGroup.HEROES_AND_MORTALS, "Power level of a mourning tradition")
    mourning_spread: int = rule(50, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Spread of a mourning tradition")
    mourning_rigidity: int = rule(40, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Rigidity of a mourning tradition")
    migration_passable_min: int = rule(15, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Least passability on foot a land must offer to draw migrants")
    migration_road_loss_pct: int = rule(20, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Migrants lost on the way per point of impassable ground (%)")
