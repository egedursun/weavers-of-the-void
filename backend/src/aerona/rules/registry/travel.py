from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class TravelRules:
    list_expeditions: int = rule(40, 1, 100000, RuleGroup.COSMOS_AND_TRAVEL, "Number of recent expeditions shown on the cosmos page")
    hidden_knower_chance: int = rule(35, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A hidden route is revealed at an end that knows the required knowledge (%)")
    hidden_base_chance: int = rule(12, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A hidden route is revealed on its own (%)")
    hidden_sensing_mortal_bonus_pct: int = rule(10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Sensing contribution of a wise mortal at the route's end (%)")
    hidden_son_bonus_pct: int = rule(8, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Sensing contribution of a son at the route's end (%)")
    sensing_min_intellect: int = rule(60, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Intellect of a mortal able to sense a hidden route")
    expedition_min_population: int = rule(1200, 0, 1000000, RuleGroup.COSMOS_AND_TRAVEL, "Minimum population of a community sending a spontaneous expedition")
    expedition_base_pct: int = rule(6, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Spontaneous expedition (% per epoch)")
    expedition_barren_pct: int = rule(15, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Expedition pressure of barren land (%)")
    expedition_barren_threshold: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Fertility counted as barren")
    expedition_crowd_pct: int = rule(10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Expedition pressure of crowding (%)")
    expedition_crowd_threshold: int = rule(20000, 0, 10000000, RuleGroup.COSMOS_AND_TRAVEL, "Population counted as crowded")
    expedition_poverty_pct: int = rule(8, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Expedition pressure of poverty (%)")
    expedition_poverty_threshold: int = rule(25, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Prosperity counted as poor")
    colony_share_pct: int = rule(10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Population share of the colony party (%)")
    lost_chance: int = rule(50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A getting-lost event on the road swallows the expedition (%)")
    colony_invasion_chance: int = rule(35, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "The colony is seen as invaders by the natives (%)")
    contact_trade_chance: int = rule(50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "First contact turns into trade (%)")
    interworld_alliance_chance: int = rule(25, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Inter-world alliance at first contact (%)")
    route_knowledge_chance: int = rule(12, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A community at the route's end learns the route knowledge (%)")
    colony_intent_chance: int = rule(
        50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "An expedition to an inhabited world becomes a colony (otherwise exploration or trade) (%)"
    )
    exploration_intent_chance: int = rule(
        35, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A non-colony spontaneous expedition becomes an exploration expedition (otherwise trade) (%)"
    )
    exploration_land_chance: int = rule(
        80, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "An exploration expedition finds a new land (region or place) on the world it reaches (%)"
    )
    alignment_period: int = rule(5, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Planetary alignment (slingshot orbit open) once every this many epochs")
    fold_min_abundance: int = rule(12, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Minimum abundance of a cosmic resource sufficient for space folding")
    route_danger_die: int = rule(20, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Danger die of a new route (1\u2026n)")
    route_danger_shift: int = rule(10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Subtracted from the new route's danger die")
    route_danger_min: int = rule(5, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Lowest danger of a route")
    route_danger_max: int = rule(95, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Highest danger of a route")
    default_vessel_speed: int = rule(40, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Speed of an expedition without a vessel or with no recorded speed")
    fast_vessel_speed: int = rule(70, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Vessel speed that shortens the journey by one epoch")
    vessel_range_per_epoch: int = rule(
        25, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Vessel range needed for each epoch of the route (below it the vessel rests on the way: +1 epoch)"
    )
    vessel_long_range: int = rule(90, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A vessel with this range shortens a long route by one epoch")
    vessel_passengers_per_crew: int = rule(20, 0, 100000, RuleGroup.COSMOS_AND_TRAVEL, "Travellers each crew member can carry (0: unlimited)")
    sky_navigation_risk_pct: int = rule(60, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Route risk multiplier for those knowing sky navigation (%)")
    void_life_risk_pct: int = rule(80, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Route risk multiplier for those knowing life in the void (%)")
    armor_risk_divisor: int = rule(250, 1, 10000, RuleGroup.COSMOS_AND_TRAVEL, "Vessel armor reduces risk: armor / this number")
    world_danger_risk_pct: int = rule(50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Share of the destination world's danger added to a journey's road risk (%)")
    ghost_ship_legend_power: int = rule(4, 1, 12, RuleGroup.COSMOS_AND_TRAVEL, "Power level of the ghost-ship legend")
    ghost_ship_legend_spread: int = rule(50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Spread of the ghost-ship legend")
    road_loss_base_pct: int = rule(10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Base share of travellers lost in a road event (%)")
    road_loss_random_pct: int = rule(25, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Random share added to travellers lost in a road event (max %)")
    default_vessel_armor: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Default armor of a vessel with no recorded armor")
    vessel_armor_loss: int = rule(10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Vessel armor loss in an attack or storm")
    colony_prosperity: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Prosperity of a new colony")
    colony_defense: int = rule(25, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Defense of a new colony")
    conquest_outpost_defense: int = rule(45, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Defense of a new conquest outpost")
    contact_cap: int = rule(3, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Maximum native communities contacted on arrival")
    invasion_relation_loss: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Relation loss with the natives in an invasion")
    contact_trade_relation: int = rule(15, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Relation gain of a first contact that turns into trade")
    alliance_relation: int = rule(15, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Relation gain of an inter-world alliance")
    uneasy_relation_loss: int = rule(5, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Relation loss of an uneasy first contact")
    exploration_charisma: int = rule(8, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Charisma gain from an exploration or pilgrimage expedition")
    trade_prosperity: int = rule(8, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Prosperity gain from a trade expedition")
    route_knowledge_cap: int = rule(2, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Maximum communities learning route knowledge per epoch")
    route_knowledge_power: int = rule(4, 1, 12, RuleGroup.COSMOS_AND_TRAVEL, "Power level of knowledge born on the road")
    route_knowledge_spread: int = rule(5, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Initial spread of knowledge born on the road")
    reveal_route_cost: int = rule(20, 0, 500, RuleGroup.COSMIC_ACTIONS, "Cost for the god to reveal a hidden route (essence)")
    expedition_cap: int = rule(
        1, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Maximum expeditions communities send on their own (per epoch; base, grows with the community count)"
    )
    expedition_cap_community_divisor: int = rule(
        100, 0, 100000, RuleGroup.COSMOS_AND_TRAVEL, "Expedition cap grows by 1 for every this many communities (0: fixed)"
    )
    expedition_visit_weight_pct: int = rule(
        50,
        0,
        10000,
        RuleGroup.COSMOS_AND_TRAVEL,
        "Expedition route choice: each previous expedition to the destination divides its selection weight by this percentage",
    )
    expedition_empty_world_weight_pct: int = rule(
        300, 0, 10000, RuleGroup.COSMOS_AND_TRAVEL, "Expedition route choice: weight multiplier of a route to a world with no people at all (%)"
    )
    colony_min_power: int = rule(2, 1, 12, RuleGroup.COSMOS_AND_TRAVEL, "Minimum power level of a new colony")
    colony_power_gap: int = rule(1, 0, 11, RuleGroup.COSMOS_AND_TRAVEL, "A new colony's power level is this much lower than the sender's")
    colony_default_piety: int = rule(50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Piety of a new colony if the party's piety is unrecorded")
    default_fertility: int = rule(
        50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Fertility assumed for a region with no recorded fertility (arrival land and barrenness)"
    )
    default_prosperity: int = rule(50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Prosperity assumed for a community with no recorded prosperity (poverty pressure)")
    special_loss_chance: int = rule(
        20, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A swallowing, dream or river-of-the-dead road event swallows the whole expedition (%)"
    )
    raid_loss_chance: int = rule(
        10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A pirate, storm or creature road event swallows the whole expedition (%; vessel armor lowers it)"
    )
    lost_caravan_legend_power: int = rule(3, 1, 12, RuleGroup.COSMOS_AND_TRAVEL, "Power level of the legend of travellers lost without a vessel")
    lost_caravan_legend_spread: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Spread of the legend of travellers lost without a vessel")
    pilgrimage_intent_chance: int = rule(
        35, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A spontaneous expedition to a world holding its god's holy site or holy world becomes a pilgrimage (%)"
    )
    conquest_intent_chance: int = rule(
        30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A warlike community's spontaneous expedition to an inhabited world becomes a conquest (%)"
    )
    conquest_min_martiality: int = rule(55, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Least martiality or defense of a community that sends conquest expeditions")
    subjugation_chance: int = rule(
        35, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "A conquest outpost makes the first natives submit without war (%; their defense lowers it)"
    )
    subjugation_defense_divisor: int = rule(200, 1, 10000, RuleGroup.COSMOS_AND_TRAVEL, "Natives' defense divided by this lowers the submission chance")
    pilgrimage_piety: int = rule(8, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Piety gained by a community whose pilgrims reach their holy site")
    pilgrimage_renown: int = rule(3, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Renown a pilgrimage brings to the community's patron son")
    wind_risk_pct: int = rule(15, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Journey danger added per point of wind at departure (%)")
