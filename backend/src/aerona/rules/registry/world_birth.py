from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class WorldBirthRules:
    regions_min: int = rule(2, 1, 50, RuleGroup.COSMOS_AND_TRAVEL, "Minimum regions in a new world")
    regions_max: int = rule(4, 1, 50, RuleGroup.COSMOS_AND_TRAVEL, "Maximum regions in a new world")
    words_min: int = rule(8, 0, 200, RuleGroup.COSMOS_AND_TRAVEL, "Minimum words in the new world's language")
    words_max: int = rule(14, 1, 200, RuleGroup.COSMOS_AND_TRAVEL, "Maximum words in the new world's language")
    resource_mechanics_max: int = rule(2, 0, 10, RuleGroup.COSMOS_AND_TRAVEL, "Maximum rules (mechanics) of the native unique resource")
    natives_max: int = rule(2, 0, 20, RuleGroup.COSMOS_AND_TRAVEL, "Maximum natives (species or people) in a new world")
    banned_names: int = rule(
        60,
        0,
        2000,
        RuleGroup.COSMOS_AND_TRAVEL,
        "Number of region, people, language, place and sky names not to be repeated in the new-world prompt (newest first)",
    )
    banned_cosmic_names: int = rule(
        200, 0, 2000, RuleGroup.COSMOS_AND_TRAVEL, "Number of world, star and foreign-god names not to be repeated in the new-world prompt (newest first)"
    )
    phoneme_set_min: int = rule(8, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Minimum distinct letters for a dialect to count as a sound set")
    star_brightness_base: int = rule(40, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "New star brightness: base")
    star_brightness_die: int = rule(55, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "New star brightness: die")
    danger_base: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "New world danger: base")
    danger_die: int = rule(40, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "New world danger: die")
    region_power: int = rule(6, 1, 12, RuleGroup.COSMOS_AND_TRAVEL, "Power level of a birth region")
    region_breadth_base: int = rule(50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Birth region breadth: base")
    region_breadth_die: int = rule(30, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Birth region breadth: die")
    sky_power: int = rule(5, 1, 12, RuleGroup.COSMOS_AND_TRAVEL, "Power level of the birth sky")
    sky_brightness_base: int = rule(40, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Birth sky brightness: base")
    sky_brightness_die: int = rule(50, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Birth sky brightness: die")
    sky_influence_base: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Birth sky influence: base")
    sky_influence_die: int = rule(50, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Birth sky influence: die")
    resource_power: int = rule(6, 1, 12, RuleGroup.COSMOS_AND_TRAVEL, "Power level of the native unique resource")
    resource_abundance_base: int = rule(50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Unique resource abundance: base")
    resource_abundance_die: int = rule(40, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Unique resource abundance: die")
    resource_value_base: int = rule(60, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Unique resource value: base")
    resource_value_die: int = rule(40, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Unique resource value: die")
    resource_might_base: int = rule(40, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Unique resource might: base")
    resource_might_die: int = rule(50, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Unique resource might: die")
    cosmic_deposit_power: int = rule(8, 1, 12, RuleGroup.COSMOS_AND_TRAVEL, "Power level of a cosmic resource deposit")
    cosmic_deposit_abundance_base: int = rule(70, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Cosmic deposit abundance: base")
    cosmic_deposit_abundance_die: int = rule(30, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Cosmic deposit abundance: die")
    cosmic_deposit_value: int = rule(95, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Cosmic deposit value")
    cosmic_deposit_might_base: int = rule(80, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Cosmic deposit might: base")
    cosmic_deposit_might_die: int = rule(20, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Cosmic deposit might: die")
    language_power: int = rule(4, 1, 12, RuleGroup.COSMOS_AND_TRAVEL, "Power level of the native language")
    language_spread: int = rule(40, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Spread of the native language")
    language_complexity_base: int = rule(40, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native language complexity: base")
    language_complexity_die: int = rule(30, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native language complexity: die")
    language_sacredness_base: int = rule(20, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native language sacredness: base")
    language_sacredness_die: int = rule(40, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native language sacredness: die")
    native_power: int = rule(4, 1, 12, RuleGroup.COSMOS_AND_TRAVEL, "Power level of the natives")
    people_population_base: int = rule(2000, 1, 10000000, RuleGroup.COSMOS_AND_TRAVEL, "Native people population: base")
    people_population_die: int = rule(8000, 1, 10000000, RuleGroup.COSMOS_AND_TRAVEL, "Native people population: die")
    people_martiality_base: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native people martiality: base")
    people_martiality_die: int = rule(50, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native people martiality: die")
    people_magic_die: int = rule(70, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native people magic: die")
    people_craft_base: int = rule(20, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native people craft: base")
    people_craft_die: int = rule(50, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native people craft: die")
    people_piety_base: int = rule(20, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native people piety: base")
    people_piety_die: int = rule(40, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native people piety: die")
    species_hp_base: int = rule(100, 1, 100000, RuleGroup.COSMOS_AND_TRAVEL, "Native species HP: base")
    species_hp_die: int = rule(400, 1, 100000, RuleGroup.COSMOS_AND_TRAVEL, "Native species HP: die")
    species_strength_base: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native species strength: base")
    species_strength_die: int = rule(60, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native species strength: die")
    species_agility_base: int = rule(20, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native species agility: base")
    species_agility_die: int = rule(60, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native species agility: die")
    species_intelligence_die: int = rule(80, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native species intelligence: die")
    species_danger_base: int = rule(20, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native species danger: base")
    species_danger_die: int = rule(70, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Native species danger: die")
