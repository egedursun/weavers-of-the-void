from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ExplorationRules:
    per_epoch_cap: int = rule(2, 0, 100, RuleGroup.EXPLORATION, "Maximum new lands mortals discover spontaneously on one world in one epoch (0 off)")
    base_chance: int = rule(4, 0, 100, RuleGroup.EXPLORATION, "A community or explorer mortal sets out to explore on its own (% per epoch)")
    min_population: int = rule(300, 0, 10000000, RuleGroup.EXPLORATION, "Minimum population (or followers) of a community setting out to explore on its own")
    crowded_fill_pct: int = rule(
        80,
        1,
        1000,
        RuleGroup.EXPLORATION,
        "If its region's fill (population / carrying capacity) is at or above this, the community counts as living on cramped land (%)",
    )
    crowded_bonus_pct: int = rule(12, 0, 100, RuleGroup.EXPLORATION, "Contribution of cramped land to a community's exploration chance (%)")
    poor_prosperity: int = rule(25, 0, 100, RuleGroup.EXPLORATION, "A community with prosperity below this counts as poor")
    hungry_bonus_pct: int = rule(10, 0, 100, RuleGroup.EXPLORATION, "Contribution of being hungry or poor to the exploration chance (%)")
    knowledge_bonus_pct: int = rule(
        8, 0, 100, RuleGroup.EXPLORATION, "Contribution to exploration chance for those knowing seafaring, pathfinding or astronomy (%)"
    )
    explorer_threshold: int = rule(120, 0, 200, RuleGroup.EXPLORATION, "Intellect + agility total for a mortal to count as having an explorer spirit")
    explorer_bonus_pct: int = rule(
        10, 0, 100, RuleGroup.EXPLORATION, "Exploration contribution of an explorer-spirited mortal (for themself or the community on their land) (%)"
    )
    new_region_pct: int = rule(40, 0, 100, RuleGroup.EXPLORATION, "Chance the found land is a new region; otherwise a new place inside a region (%)")
    land_power: int = rule(3, 1, 12, RuleGroup.EXPLORATION, "Power level of a discovered land")
    land_stat_base: int = rule(15, 0, 100, RuleGroup.EXPLORATION, "Base of the breadth, magic and mystery of a discovered land")
    land_stat_die: int = rule(60, 1, 100, RuleGroup.EXPLORATION, "Die added to the breadth, magic and mystery of a discovered land (1\u2026n)")
    land_fertility_base: int = rule(35, 0, 100, RuleGroup.EXPLORATION, "Base fertility of a discovered land")
    land_fertility_die: int = rule(50, 1, 100, RuleGroup.EXPLORATION, "Die added to the fertility of a discovered land (1\u2026n)")
    land_danger_base: int = rule(10, 0, 100, RuleGroup.EXPLORATION, "Base danger of a discovered land")
    land_danger_die: int = rule(50, 1, 100, RuleGroup.EXPLORATION, "Die added to the danger of a discovered land (1\u2026n)")
    pioneer_chance: int = rule(50, 0, 100, RuleGroup.EXPLORATION, "Pioneers settle the land the community found (doubled on cramped land) (%)")
    pioneer_share_pct: int = rule(8, 0, 100, RuleGroup.EXPLORATION, "Population share of the pioneer party (%)")
    pioneer_min_population: int = rule(100, 1, 1000000, RuleGroup.EXPLORATION, "Minimum population of a pioneer settlement")
    pioneer_prosperity: int = rule(35, 0, 100, RuleGroup.EXPLORATION, "Prosperity of a pioneer settlement")
    pioneer_defense: int = rule(20, 0, 100, RuleGroup.EXPLORATION, "Defense of a pioneer settlement")
    pioneer_default_piety: int = rule(50, 0, 100, RuleGroup.EXPLORATION, "Piety of pioneers coming from a community with no recorded piety")
    map_distance: int = rule(
        300, 50, 2000, RuleGroup.EXPLORATION, "Distance of the new region on the map from the region it was found from (close enough to be neighbours)"
    )
    map_attempts: int = rule(12, 1, 360, RuleGroup.EXPLORATION, "Number of directions tried when searching for the new region's map position")
    route_search_chance: int = rule(
        6,
        0,
        100,
        RuleGroup.EXPLORATION,
        "A community or mortal knowing a way to other worlds (sky navigation, gate science, pathfinding, magic or a flying mount) searches for a route on its own (% per epoch)",
    )
    route_search_cap: int = rule(
        1, 0, 100, RuleGroup.EXPLORATION, "Maximum communities or mortals searching for a route on their own in the cosmos in one epoch (0 off)"
    )
    crowded_communities_per_region: int = rule(
        3, 1, 100, RuleGroup.EXPLORATION, "If communities (peoples + settlements) per region on a world are at or above this, land counts as cramped"
    )
    free_land_creation: int = rule(
        1, 0, 1, RuleGroup.EXPLORATION, "On cramped land the son's first land creation (region or place) in the epoch costs no action (1 on, 0 off)"
    )
    land_creation_essence: int = rule(10, 0, 10000, RuleGroup.EXPLORATION, "Essence reward for a son creating a new region or place on cramped land")
    land_creation_renown: int = rule(3, 0, 10000, RuleGroup.EXPLORATION, "Renown reward for a son creating a new region or place on cramped land")
    cosmos_stagnant_epochs: int = rule(
        8, 1, 1000, RuleGroup.EXPLORATION, "If no new world has been born for this many epochs, sons able to birth worlds are reminded of the cosmos"
    )
    foreign_god_raise_land_chance: int = rule(8, 0, 100, RuleGroup.EXPLORATION, "An awake foreign god raises a new land on its own world (% per epoch)")
    tool_per_epoch: int = rule(
        1, 0, 20, RuleGroup.EXPLORATION, "discover_land (toprak_kesfet): maximum discoveries by one mortal per epoch (0 disables the tool)"
    )
    tool_success_threshold: int = rule(
        45,
        0,
        200,
        RuleGroup.EXPLORATION,
        "discover_land: success threshold (d100 + intellect or craft / MORTAL_TOOLS.route_intellect_divisor + knowledge bonus)",
    )
    tool_knowledge_bonus: int = rule(15, 0, 200, RuleGroup.EXPLORATION, "discover_land: die bonus for those knowing seafaring, pathfinding or astronomy")
    summary_list: int = rule(12, 1, 1000, RuleGroup.EXPLORATION, "Number of recent discoveries shown in the exploration summary")
