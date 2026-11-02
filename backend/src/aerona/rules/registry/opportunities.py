from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class OpportunitiesRules:
    list_max: int = rule(5, 1, 50, RuleGroup.OPPORTUNITIES, "Maximum records listed in one opportunity line")
    stale_epochs: int = rule(4, 1, 100, RuleGroup.OPPORTUNITIES, 'A story untouched for this many epochs counts as "about to be forgotten"')
    long_thread_steps: int = rule(8, 1, 200, RuleGroup.OPPORTUNITIES, 'After this many advances a story counts as "should be concluded"')
    silence_epochs: int = rule(3, 1, 100, RuleGroup.OPPORTUNITIES, "Reminder to a son who hasn't talked with his siblings for this many epochs")
    rich_essence: int = rule(150, 0, 100000, RuleGroup.OPPORTUNITIES, 'Essence for a "great deed" reminder to the Creator')
    list_short: int = rule(4, 1, 50, RuleGroup.OPPORTUNITIES, "Maximum records in short opportunity lists")
    list_narrow: int = rule(3, 1, 50, RuleGroup.OPPORTUNITIES, "Maximum records in the narrowest opportunity lists")
    list_wide: int = rule(6, 1, 100, RuleGroup.OPPORTUNITIES, "Maximum records in wide opportunity lists")
    life_people_surplus: int = rule(
        2, 0, 50, RuleGroup.OPPORTUNITIES, '"Breathe life": if the number of peoples doesn\'t exceed the number of regions by this much'
    )
    life_mortals_below: int = rule(6, 0, 200, RuleGroup.OPPORTUNITIES, '"Breathe life": if named mortals are fewer than this')
    life_species_below: int = rule(4, 0, 200, RuleGroup.OPPORTUNITIES, '"Breathe life": if species are fewer than this')
    rival_relation: int = rule(20, 0, 100, RuleGroup.OPPORTUNITIES, "Relation with a sibling counted as a rival: below minus this")
    target_sibling_relation: int = rule(
        25, 0, 100, RuleGroup.OPPORTUNITIES, "Relation with a sibling whose creations are pointed out as targets: below minus this"
    )
    rebel_loyalty: int = rule(40, 0, 100, RuleGroup.OPPORTUNITIES, "Rebellion reminder if loyalty is below this")
    fading_existence: int = rule(20, 0, 100, RuleGroup.OPPORTUNITIES, '"You are about to fade out" if existence is at or below this')
    fading_sons_existence: int = rule(25, 0, 100, RuleGroup.OPPORTUNITIES, 'To the god: sons with existence at or below this are "being forgotten"')
    apocalypse_warning_pct: int = rule(50, 0, 100, RuleGroup.OPPORTUNITIES, "Apocalypse reminder to the god: at this percentage of the threshold")
    hungry_food: int = rule(60, 0, 1000, RuleGroup.OPPORTUNITIES, "Worshippers count as hungry: food below this")
    granary_food: int = rule(60, 0, 1000, RuleGroup.OPPORTUNITIES, 'To a mortal "your granary is emptying": food below this')
    discontented: int = rule(30, 0, 100, RuleGroup.OPPORTUNITIES, "A class counts as discontented: satisfaction below this")
    friendly_neighbor: int = rule(45, -100, 100, RuleGroup.OPPORTUNITIES, "Loving neighbour: community relation at or above this")
    monster_danger: int = rule(50, 0, 100, RuleGroup.OPPORTUNITIES, "Dangerous creature: danger at or above this")
    tense_neighbor: int = rule(
        20, 0, 100, RuleGroup.OPPORTUNITIES, 'To a mortal "tense neighbour": community relation below minus this (with no hostility link)'
    )
    tension_first: int = rule(
        1, 0, 1, RuleGroup.OPPORTUNITIES, "Tension lines (rivals, hostilities, wars, rebellion) are placed at the top of the opportunity list (1 on, 0 off)"
    )
    challenge_god_strength: int = rule(110, 0, 1000, RuleGroup.OPPORTUNITIES, "Suggestion to challenge a god: strength + agility at or above this")
    untried_epochs: int = rule(4, 1, 100, RuleGroup.OPPORTUNITIES, "A tool unused for this many epochs gets a concrete suggestion")
    untried_count: int = rule(2, 0, 20, RuleGroup.OPPORTUNITIES, "Most unused tools suggested per turn")
    rival_options: int = rule(3, 1, 20, RuleGroup.OPPORTUNITIES, "Most options written for an action against a rival sibling")
    overused_uses: int = rule(6, 1, 1000, RuleGroup.OPPORTUNITIES, "A son or mortal using one tool this many times in the recent epochs is reminded to vary")
    essence_margin: int = rule(20, 0, 1000, RuleGroup.OPPORTUNITIES, "Essence that must remain above a cost before a costly birth is suggested")
    few_celestials: int = rule(2, 0, 100, RuleGroup.OPPORTUNITIES, "Hanging a celestial body is suggested when a world's sky holds fewer than this")
    few_laws: int = rule(2, 0, 100, RuleGroup.OPPORTUNITIES, "Decreeing a natural law is suggested when a world has fewer than this")
    lend_min_wealth: int = rule(50, 0, 100, RuleGroup.OPPORTUNITIES, "Least wealth (or prosperity) of a mortal for lending to be suggested")
