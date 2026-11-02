from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class KnowledgeRules:
    diffusion_chance: int = rule(18, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Knowledge spreads along trade and rule links (%)")
    diffusion_cap: int = rule(
        4, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Maximum knowledge spreading along links per epoch (base; grows with the community count)"
    )
    diffusion_cap_community_divisor: int = rule(
        40, 0, 100000, RuleGroup.RELIGION_AND_LANGUAGE, "Knowledge spread cap grows by 1 for every this many communities (0: fixed)"
    )
    writing_diffusion_mult: int = rule(2, 1, 20, RuleGroup.RELIGION_AND_LANGUAGE, "Knowledge-spread multiplier from those knowing writing (times)")
    language_spread_chance: int = rule(20, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Under the one-language law a language spreads along links (%)")
    dark_age_forget_cap: int = rule(2, 0, 50, RuleGroup.CIVILIZATION, "Maximum knowledge forgotten per epoch")
    dark_age_min_severity: int = rule(70, 0, 100, RuleGroup.CIVILIZATION, "Minimum severity of an event counted as ruin")
    dark_age_scribe_pct: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "Scribe share that protects knowledge from being forgotten (%)")
    relic_rediscovery_cap: int = rule(1, 0, 20, RuleGroup.CIVILIZATION, "Maximum knowledge rediscovered from remnants per epoch")
    relic_min_scribe_pct: int = rule(7, 0, 100, RuleGroup.CIVILIZATION, "Minimum scribe share of a community able to decipher knowledge from remnants (%)")
    spread_base: int = rule(8, 0, 100, RuleGroup.CIVILIZATION, "Base spread of a known knowledge")
    spread_per_knower: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "Contribution of each knowing community to knowledge spread")
    spread_default: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "Spread assumed for a knowledge with no spread record")
    spread_step: int = rule(5, 0, 100, RuleGroup.CIVILIZATION, "Maximum per-epoch change of knowledge spread")
    dark_age_prosperity: int = rule(12, 0, 100, RuleGroup.CIVILIZATION, "Prosperity below this counts as ruin (dark age)")
    dark_age_forget_chance: int = rule(30, 0, 100, RuleGroup.CIVILIZATION, "Knowledge forgotten after ruin (%)")
    dark_age_forget_protected_chance: int = rule(5, 0, 100, RuleGroup.CIVILIZATION, "Forgetting when there are scribes or a library (%)")
    relic_decipher_chance: int = rule(12, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Scribes decipher lost knowledge from remnants (%)")
    level_cap: int = rule(10, 1, 10, RuleGroup.CIVILIZATION, "Highest level a knowledge can reach")
    level_step_pct: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "Each knowledge level above the first adds this much to its branch effect (%)")
    level_multiplier_cap_pct: int = rule(180, 100, 1000, RuleGroup.CIVILIZATION, "Highest multiplier the level can give a branch effect (%)")
    ratio_floor_pct: int = rule(20, 0, 100, RuleGroup.CIVILIZATION, "Lowest severity a level can push a softening branch effect to (%)")
    branch_record_cap: int = rule(
        2, 1, 100, RuleGroup.CIVILIZATION, "Most separate knowledge records one branch may hold in a world; later ones find or deepen an existing one"
    )
    level_up_spread: int = rule(4, 0, 100, RuleGroup.CIVILIZATION, "Spread gained when a knowledge rises a level")
    develop_level_gain: int = rule(1, 1, 10, RuleGroup.CIVILIZATION, "Levels a mortal adds when it develops a knowledge it already holds")
    craft_level_bonus: int = rule(1, 0, 10, RuleGroup.CIVILIZATION, "Extra level for a strongly crafting community when it develops a knowledge")
    deepen_chance: int = rule(4, 0, 100, RuleGroup.CIVILIZATION, "Engine: base chance a knowing community deepens one of its knowledges per epoch (%)")
    deepen_scribe_divisor: int = rule(4, 1, 1000, RuleGroup.CIVILIZATION, "Engine: scribe share (%) divided by this is added to the deepening chance (%)")
    deepen_min_prosperity: int = rule(35, 0, 100, RuleGroup.CIVILIZATION, "Engine: communities below this prosperity cannot deepen their knowledge")
    deepen_cap: int = rule(4, 0, 100, RuleGroup.CIVILIZATION, "Engine: most knowledges deepened per epoch")
    discovery_chance: int = rule(14, 0, 100, RuleGroup.CIVILIZATION, "Engine: chance per world and epoch that a branch nobody knows there is discovered (%)")
    discovery_cap: int = rule(2, 0, 50, RuleGroup.CIVILIZATION, "Engine: most new branches discovered per epoch")
    discovery_candidates: int = rule(5, 1, 100, RuleGroup.CIVILIZATION, "Engine: most-scribed communities per world that may discover a new branch")
    discovery_min_scribe_pct: int = rule(4, 0, 100, RuleGroup.CIVILIZATION, "Engine: lowest scribe share of a community able to discover a new branch (%)")
    rare_branch_weight_pct: int = rule(
        300, 0, 10000, RuleGroup.CIVILIZATION, "Engine: discovery weight of a rare branch whose prerequisite is known (%; an ordinary branch is 100)"
    )
    discovery_spread: int = rule(6, 0, 100, RuleGroup.CIVILIZATION, "First spread of a newly discovered branch")
    discovery_power: int = rule(3, 1, 12, RuleGroup.CIVILIZATION, "Power level of a newly discovered branch")
    decline_chance: int = rule(20, 0, 100, RuleGroup.CIVILIZATION, "Engine: chance per epoch a knowledge whose every holder is in ruin loses a level (%)")
    decline_prosperity: int = rule(20, 0, 100, RuleGroup.CIVILIZATION, "Engine: a holder below this prosperity counts as ruined for knowledge decline")
    decline_cap: int = rule(3, 0, 100, RuleGroup.CIVILIZATION, "Engine: most knowledges losing a level per epoch")
    creator_deepen_cost: int = rule(
        10, 0, 1000, RuleGroup.INTERVENTIONS_IN_THE_MORTAL_WORLD, "Creator: essence to deepen a knowledge by one level (blunting is free)"
    )
    son_advance_cost: int = rule(6, 0, 1000, RuleGroup.GOD_AND_SON_COSTS, "Son: essence cost of the advance knowledge tool")
    son_level_per_power: int = rule(2, 1, 10, RuleGroup.GOD_AND_SON_COSTS, "Son: advance knowledge reaches at most power cap times this many levels")
    hint_empty_branches: int = rule(6, 0, 50, RuleGroup.CIVILIZATION, "Unknown branches named in opportunities and errors")
