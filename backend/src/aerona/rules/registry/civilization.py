from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class CivilizationRules:
    independence_war_chance: int = rule(60, 0, 100, RuleGroup.CIVILIZATION, "Independence turns into war (%)")
    federation_chance: int = rule(25, 0, 100, RuleGroup.CIVILIZATION, "An inter-world federation is founded (%)")
    previous_creation_relic_chance: int = rule(35, 0, 100, RuleGroup.CIVILIZATION, "A remnant of a previous creation is found (%)")
    city_state_population: int = rule(3000, 0, 100000000, RuleGroup.CIVILIZATION, "Minimum population to become a city")
    city_state_knowledge: int = rule(1, 0, 100, RuleGroup.CIVILIZATION, "Minimum known knowledge to become a city")
    realm_population: int = rule(20000, 0, 100000000, RuleGroup.CIVILIZATION, "Minimum population of a realm with no ruled places")
    realm_ruled_places: int = rule(1, 0, 100, RuleGroup.CIVILIZATION, "Minimum ruled places to become a realm")
    realm_knowledge: int = rule(3, 0, 100, RuleGroup.CIVILIZATION, "Minimum known knowledge to become a realm")
    empire_region_pct: int = rule(
        50,
        0,
        100,
        RuleGroup.CIVILIZATION,
        "Share of regions dominated for a world power (% of settled regions; regions dominated by itself, its subjects and its tributaries)",
    )
    empire_population_pct: int = rule(
        25,
        0,
        100,
        RuleGroup.CIVILIZATION,
        "For a world power (if region share is not enough): be the most populous political power of its world and hold this share of the world's population (%; including subjects and tributaries)",
    )
    empire_min_world_regions: int = rule(2, 1, 1000, RuleGroup.CIVILIZATION, "Minimum regions of a world on which a world power can count")
    interstellar_worlds: int = rule(2, 1, 100, RuleGroup.CIVILIZATION, "Minimum worlds spread across for an interstellar power")
    cosmic_worlds: int = rule(3, 1, 100, RuleGroup.CIVILIZATION, "Minimum worlds spread across for a cosmic power")
    stage_demotion_pct: int = rule(
        15,
        0,
        100,
        RuleGroup.CIVILIZATION,
        "Demotion margin: a community at a stage regresses only when it drops this percentage below the population and dominated-share thresholds (so it doesn't flicker at the threshold)",
    )
    stage_min_epochs: int = rule(
        3,
        0,
        100,
        RuleGroup.CIVILIZATION,
        "A community that changes stage doesn't reverse direction for at least this many epochs (a riser doesn't fall back, a faller doesn't rise back; 0: off)",
    )
    colony_independence_min_age: int = rule(3, 0, 100, RuleGroup.CIVILIZATION, "Minimum age of a colony that can seek independence (epochs)")
    colony_far_cooling: int = rule(4, 0, 100, RuleGroup.CIVILIZATION, "Per-epoch cooling of a colony on another world toward its homeland")
    colony_near_cooling: int = rule(1, 0, 100, RuleGroup.CIVILIZATION, "Per-epoch cooling of a colony on the same world toward its homeland")
    colony_far_independence_chance: int = rule(12, 0, 100, RuleGroup.CIVILIZATION, "A colony on another world declares independence (%)")
    colony_near_independence_chance: int = rule(4, 0, 100, RuleGroup.CIVILIZATION, "A colony on the same world declares independence (%)")
    colony_prosperity_base: int = rule(40, 0, 100, RuleGroup.CIVILIZATION, "Colony prosperity at which the independence chance starts to rise")
    colony_prosperity_divisor: int = rule(
        400, 10, 100000, RuleGroup.CIVILIZATION, "Prosperity contribution to independence: (prosperity \u2212 base) / this number"
    )
    colony_grudge_bonus_pct: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "Independence contribution of a colony estranged from its homeland (%)")
    federation_min_members: int = rule(3, 2, 100, RuleGroup.CIVILIZATION, "Minimum members of a federation")
    federation_max: int = rule(
        1, 0, 100, RuleGroup.CIVILIZATION, "Maximum simultaneous federations in the cosmos (a community can only be a member of one; 0 disables)"
    )
    federation_min_worlds: int = rule(2, 1, 100, RuleGroup.CIVILIZATION, "Minimum worlds federation members are spread across")
    federation_power: int = rule(6, 1, 12, RuleGroup.CIVILIZATION, "Power level of a federation")
    federation_strength: int = rule(50, 0, 100, RuleGroup.CIVILIZATION, "Strength of a federation")
    federation_wealth: int = rule(60, 0, 100, RuleGroup.CIVILIZATION, "Wealth of a federation")
    federation_sway: int = rule(70, 0, 100, RuleGroup.CIVILIZATION, "Sway of a federation")
    relic_site_power: int = rule(7, 1, 12, RuleGroup.CIVILIZATION, "Power level of a previous-creation remnant")
    relic_site_danger: int = rule(50, 0, 100, RuleGroup.CIVILIZATION, "Base danger of the remnant")
    relic_site_danger_die: int = rule(30, 1, 100, RuleGroup.CIVILIZATION, "Danger die of the remnant")
    relic_site_fertility: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "Fertility of the remnant")
    relic_site_mystery: int = rule(95, 0, 100, RuleGroup.CIVILIZATION, "Mystery of the remnant")
    heirloom_power: int = rule(8, 1, 12, RuleGroup.CIVILIZATION, "Power level of a previous-creation heirloom")
    heirloom_damage: int = rule(40, 0, 100, RuleGroup.CIVILIZATION, "Base damage of the heirloom")
    heirloom_damage_die: int = rule(40, 1, 100, RuleGroup.CIVILIZATION, "Damage die of the heirloom")
    heirloom_protection: int = rule(30, 0, 100, RuleGroup.CIVILIZATION, "Base protection of the heirloom")
    heirloom_protection_die: int = rule(40, 1, 100, RuleGroup.CIVILIZATION, "Protection die of the heirloom")
    heirloom_might: int = rule(80, 0, 100, RuleGroup.CIVILIZATION, "Base might of the heirloom")
    heirloom_might_die: int = rule(20, 1, 100, RuleGroup.CIVILIZATION, "Might die of the heirloom")
    heirloom_curse: int = rule(50, 0, 100, RuleGroup.CIVILIZATION, "Base curse of the heirloom")
    heirloom_curse_die: int = rule(40, 1, 100, RuleGroup.CIVILIZATION, "Curse die of the heirloom")
    ancient_knowledge_power: int = rule(7, 1, 12, RuleGroup.CIVILIZATION, "Power level of previous-creation knowledge")
    ancient_knowledge_level: int = rule(7, 1, 10, RuleGroup.CIVILIZATION, "Level of previous-creation knowledge")
    ancient_knowledge_forbidden_chance: int = rule(50, 0, 100, RuleGroup.CIVILIZATION, "Previous-creation knowledge is forbidden knowledge (%)")
    loan_chance: int = rule(10, 0, 100, RuleGroup.ECONOMY, "A wealthy community lends to its poor neighbour on its own (% per epoch)")
    loan_lender_min: int = rule(55, 0, 100, RuleGroup.ECONOMY, "Minimum wealth or prosperity of a community able to lend")
    loan_borrower_max: int = rule(35, 0, 100, RuleGroup.ECONOMY, "Maximum wealth or prosperity of a community asking for a loan")
    loan_amount: int = rule(10, 1, 100, RuleGroup.ECONOMY, "Amount of a spontaneous loan")
    loan_term: int = rule(3, 1, 50, RuleGroup.ECONOMY, "Term of a spontaneous loan (epochs)")
    loan_distance: int = rule(3, 0, 99, RuleGroup.ECONOMY, "Farthest distance between borrowing communities (steps)")
    loan_repay_chance: int = rule(40, 0, 100, RuleGroup.ECONOMY, "A debtor able to pay repays on its own (% per epoch)")
    loan_repay_reserve: int = rule(10, 0, 100, RuleGroup.ECONOMY, "Wealth or prosperity the debtor must keep after paying")
    loan_relation: int = rule(5, 0, 100, RuleGroup.ECONOMY, "Relation contribution of a loan (spontaneous, decreed or lent by a mortal agent)")
    loan_repay_relation: int = rule(8, 0, 100, RuleGroup.ECONOMY, "Relation contribution of a repaid loan (all loans of the engine and mortals)")
    loan_default_relation: int = rule(20, 0, 100, RuleGroup.ECONOMY, "Relation damage of a loan not repaid on time (all loans of the engine and mortals)")
    barter_chance: int = rule(8, 0, 100, RuleGroup.ECONOMY, "Trade partners barter items on their own (% per epoch)")
    barter_max_value_diff: int = rule(25, 0, 100, RuleGroup.ECONOMY, "Maximum value difference between two bartered things")
    barter_relation: int = rule(6, 0, 100, RuleGroup.ECONOMY, "Relation contribution of a spontaneous barter")
    adoption_chance: int = rule(6, 0, 100, RuleGroup.HEROES_AND_MORTALS, "An old mortal adopts a nearby orphaned youth on their own (% per epoch)")
    adoption_max_child_age: int = rule(16, 0, 1000, RuleGroup.HEROES_AND_MORTALS, "Oldest age that can be adopted (years)")
    adoption_min_age_gap: int = rule(15, 0, 1000, RuleGroup.HEROES_AND_MORTALS, "Minimum age gap between adopter and child (years)")
    adoption_distance: int = rule(1, 0, 99, RuleGroup.HEROES_AND_MORTALS, "Farthest distance between adopter and child (steps)")
    adoption_relation: int = rule(10, 0, 100, RuleGroup.HEROES_AND_MORTALS, "Relation contribution of adoption")
    treaty_chance: int = rule(
        8, 0, 100, RuleGroup.CIVILIZATION, "Communities of two worlds connected by an open route make a treaty on their own (% per epoch)"
    )
    treaty_trade_min_relation: int = rule(0, -100, 100, RuleGroup.CIVILIZATION, "Minimum relation for an inter-world trade treaty")
    treaty_alliance_min_relation: int = rule(25, -100, 100, RuleGroup.CIVILIZATION, "Minimum relation for an inter-world alliance of trade partners")
    treaty_candidates: int = rule(4, 1, 100, RuleGroup.CIVILIZATION, "Number of most populous communities examined at each end of the route for a treaty")
    treaty_relation: int = rule(12, 0, 100, RuleGroup.CIVILIZATION, "Relation contribution of a spontaneous inter-world treaty")
    unlock_expedition_tier: int = rule(
        1, 0, 5, RuleGroup.CIVILIZATION, "Civilization tier that unlocks sending expeditions to other worlds (0 tribe to 5 cosmic power)"
    )
    unlock_colony_tier: int = rule(1, 0, 5, RuleGroup.CIVILIZATION, "Civilization tier that unlocks founding colonies on other worlds")
    unlock_conquest_tier: int = rule(2, 0, 5, RuleGroup.CIVILIZATION, "Civilization tier that unlocks conquest expeditions")
    unlock_route_search_tier: int = rule(1, 0, 5, RuleGroup.CIVILIZATION, "Civilization tier that unlocks searching for routes between worlds")
    unlock_shipbuilding_tier: int = rule(2, 0, 5, RuleGroup.CIVILIZATION, "Civilization tier that unlocks building ships that sail between worlds")
    unlock_treaty_tier: int = rule(1, 0, 5, RuleGroup.CIVILIZATION, "Civilization tier that unlocks interworld treaties")
    unlock_federation_tier: int = rule(2, 0, 5, RuleGroup.CIVILIZATION, "Civilization tier that unlocks joining an interworld federation")
    unlock_loan_tier: int = rule(0, 0, 5, RuleGroup.CIVILIZATION, "Civilization tier that unlocks lending to other communities")
    unlock_exploration_tier: int = rule(0, 0, 5, RuleGroup.CIVILIZATION, "Civilization tier that unlocks exploring unknown lands")
    unlock_deposit_claim_tier: int = rule(0, 0, 5, RuleGroup.CIVILIZATION, "Civilization tier that unlocks claiming a deposit of the cosmic travel resource")
