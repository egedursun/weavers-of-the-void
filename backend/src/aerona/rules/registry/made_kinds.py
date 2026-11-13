from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

W = RuleGroup.WAR_AND_DIPLOMACY
M = RuleGroup.MATERIALS
S = RuleGroup.SETTLEMENTS
C = RuleGroup.COSMOS
B = RuleGroup.BODY
H = RuleGroup.HEROES_AND_MORTALS


@dataclass(frozen=True)
class ArmamentRules:
    forge_share_pct: int = rule(20, 0, 100, M, "Share of a holder's weapons, armour and siege materiel forged into pieces of its models each epoch (%)")
    battle_wear: int = rule(10, 0, 100, W, "Condition a carried piece of equipment loses in a battle")
    capture_pct: int = rule(30, 0, 100, W, "Share of the pieces dropped by a beaten army that the victor takes into its stores (%)")
    victory_renown: int = rule(2, 0, 100, W, "Renown a model carried by the winning side of a battle gains")
    son_model_essence: int = rule(10, 0, 10000, M, "Essence a son spends to give a community an equipment model of its own")


@dataclass(frozen=True)
class VehicleRules:
    tribe_size: int = rule(2, 0, 4, W, "Largest hull a tribe can build, counted from small (0) to colossal (4); technology alone opens a frame")
    city_state_size: int = rule(3, 0, 4, W, "Largest hull a city-state can build, counted from small (0) to colossal (4)")
    kingdom_size: int = rule(4, 0, 4, W, "Largest hull a kingdom can build, counted from small (0) to colossal (4)")
    empire_size: int = rule(4, 0, 4, W, "Largest hull a world empire can build, counted from small (0) to colossal (4)")
    interstellar_size: int = rule(4, 0, 4, W, "Largest hull an interstellar power can build, counted from small (0) to colossal (4)")
    cosmic_size: int = rule(4, 0, 4, W, "Largest hull a cosmic power can build, counted from small (0) to colossal (4)")
    deflect_pct: int = rule(150, 1, 1000, W, "Armour at which a section turns aside every hit; a section turns aside hits in proportion to its armour (%)")
    fire_spread_pct: int = rule(35, 0, 100, W, "Chance a burning section sets a neighbouring section alight (%)")
    explosion_hits: int = rule(2, 0, 10, W, "Hits an exploding section deals to each neighbouring section")
    flood_spread_pct: int = rule(40, 0, 100, W, "Chance a flooding section floods a neighbouring section (%)")
    breach_crew_pct: int = rule(30, 0, 100, W, "Share of a vehicle's crew a breached section kills (%)")
    crash_pct: int = rule(30, 0, 100, W, "Chance a disabled lift section brings the vehicle down (%)")
    panic_pct: int = rule(25, 0, 100, W, "Chance a disabled draft team overturns its vehicle (%)")
    section_hit: int = rule(35, 1, 100, W, "Condition a single vessel's section loses to a hit")
    battle_hits_pct: int = rule(100, 0, 500, W, "Hits a vehicle group takes for each share of its army lost in battle (%)")
    salvage_pct: int = rule(40, 0, 100, W, "Share of a lost vehicle's structure salvaged as materials by the holder of the field (%)")
    prize_pct: int = rule(50, 0, 100, W, "Share of a beaten group's disabled vehicles the victor takes as prizes (%)")
    yard_points: int = rule(6, 0, 1000, W, "Building points a yard of level one gives each epoch")
    cost_per_point: int = rule(30, 1, 10000, W, "Vehicle cost one building point covers")
    park_cap: int = rule(20, 0, 10000, W, "Most vehicles of one type a realm keeps in its park before its yards stop building it")
    cart_points: int = rule(4, 0, 1000, W, "Building points a market, stable or lumber camp of level one gives each epoch to carts, wagons and pack trains")
    cargo_per_baggage: int = rule(
        10, 1, 1000, W, "Cargo of an army's land vehicles that bears one point of its baggage, so that point no longer slows its march"
    )
    coin_share: int = rule(4, 1, 100, W, "A vehicle's cost and upkeep are divided by this to give the coin paid")
    ring_points_pct: int = rule(200, 100, 1000, C, "Building points an orbital ring gives against a space works of the same level (%)")
    unpaid_decay: int = rule(5, 0, 100, W, "Condition a vehicle group loses in an epoch its upkeep goes unpaid")
    park_repair: int = rule(2, 0, 100, W, "Section states a group laid up in its park mends each epoch")
    walk_pace: int = rule(40, 1, 500, W, "Speed a marching soldier keeps; an army's land vehicles set its pace against it")
    son_type_essence: int = rule(20, 0, 10000, W, "Essence a son spends to give a community a vehicle type of its own")


@dataclass(frozen=True)
class IntegrityRules:
    damaged_at: int = rule(75, 1, 100, S, "Condition below which a section of a structure counts as damaged")
    disabled_at: int = rule(40, 1, 100, S, "Condition below which a section of a structure counts as disabled")
    fire_spread_pct: int = rule(60, 0, 300, S, "Share of a burning section's damage that passes to a neighbour, scaled by the neighbour's flammability (%)")
    collapse_hit: int = rule(40, 0, 100, S, "Damage a collapsing or exploding section deals to each neighbour")
    rebuild_step: int = rule(5, 0, 100, S, "Condition a kept structure rebuilds into each destroyed section each epoch")
    keep_breaches: int = rule(3, 0, 20, W, "Breaches a siege gains when the besieged citadel's keep falls")
    desecration_piety: int = rule(15, 0, 100, S, "Piety a community loses when the sanctum of one of its temples is destroyed")
    archive_loss_pct: int = rule(30, 0, 100, S, "Share of a house of knowledge's volumes lost when its archive is disabled or destroyed (%)")
    stores_loss_pct: int = rule(40, 0, 100, S, "Share of a community's grain lost when the stores of a granary or warehouse are destroyed (%)")
    bridge_scar: int = rule(60, 0, 100, S, "Depth of the downed-bridge scar a destroyed span leaves on its land")
    flood_loss_pct: int = rule(25, 0, 100, S, "Share of a community's grain lost to the flood when a sluice bursts (%)")
    breach_population_pct: int = rule(10, 0, 100, S, "Share of a settlement's people lost when its habitat decks are breached (%)")
    catastrophe_loss: int = rule(30, 0, 100, S, "Damage the failure of a megastructure's control core deals to every other structure of its settlement")
    son_type_essence: int = rule(10, 0, 10000, S, "Essence a son spends to give a community a building type of its own")
    draw_skill: int = rule(30, 0, 100, S, "Engineering a mortal needs to draw a building type for its people")


@dataclass(frozen=True)
class MegastructureRules:
    collector_coin: int = rule(400, 0, 1000000, C, "Coin a star collector of level one gives its owner each epoch")
    collector_dim: int = rule(2, 0, 100, C, "Brightness a working star collector takes from its star each epoch")
    collector_floor: int = rule(40, 0, 100, C, "Brightness below which a star collector no longer dims its star")
    collector_regard: int = rule(5, 0, 100, C, "Relation the star's worshippers lose toward the owner of a star collector each epoch")
    collector_flare: int = rule(20, 0, 100, C, "Brightness a star regains in a flare when its collector's control core fails")
    beacon_relief: int = rule(5, 0, 100, C, "Danger a working beacon takes off each route touching its world each epoch")
    ring_relief: int = rule(3, 0, 100, C, "Danger a working orbital ring takes off each cosmic route of its world each epoch")
    engine_step_pct: int = rule(2, 0, 100, C, "Most a working planetary engine moves its world toward the set orbit each epoch (hundredths of an orbit unit)")
    engine_shock_pct: int = rule(10, -100, 100, C, "Change to a world's orbit when its planetary engine's control core fails (%)")


@dataclass(frozen=True)
class UnitTypeRules:
    draw_pct: int = rule(25, 0, 100, W, "Chance each epoch a realm's marshal draws its own kind of soldier for a role its template asks for (%)")
    refit_pct: int = rule(10, 0, 100, W, "Chance each epoch a realm refits a kind of soldier once better equipment is known (%)")
    spread_pct: int = rule(5, 0, 100, W, "Chance each epoch an ally learns a kind of soldier for a role it has none for (%)")
    draft_skill: int = rule(30, 0, 100, W, "Tactics or strategy a mortal needs to draft a kind of soldier for its realm or town")


@dataclass(frozen=True)
class CuisineRules:
    invent_pct: int = rule(8, 0, 100, S, "Chance each epoch a people comes to cook a new dish from its stores (%)")
    starting_dishes: int = rule(
        3, 0, 8, S, "Dishes of its own a people cooks from its stores before new ones come only by chance: a staple, a drink, a feast dish and on"
    )
    ration_keeping: int = rule(3, 0, 20, S, "Epochs a dish must keep for a people to take it as a ration")
    portion: int = rule(10, 0, 10000, S, "Ingredients a community spends to cook one of its dishes at full popularity")
    delight_pct: int = rule(10, 0, 100, S, "Share of a dish's delight that calms its community's unrest when cooked (%)")
    prestige_pct: int = rule(5, 0, 100, S, "Share of a feast dish's or delicacy's prestige added to its town each epoch it is cooked (%)")
    rite_pct: int = rule(5, 0, 100, S, "Share of a rite dish's delight added to its community's piety when cooked (%)")
    nourish_pct: int = rule(3, 0, 100, S, "Share of a staple or remedy's nourishment added to its community's prosperity when cooked (%)")
    taste_gain: int = rule(2, 0, 100, S, "Popularity a dish gains each epoch it is cooked")
    taste_loss: int = rule(5, 0, 100, S, "Popularity a dish loses each epoch its community cannot cook it")
    ration_days: int = rule(5, 0, 1000, W, "Supply days each epoch of keeping in a realm's best ration adds to its armies")
    spread_pct: int = rule(15, 0, 100, S, "Chance a convoy that arrives teaches its destination one of its origin's dishes (%)")
    son_dish_essence: int = rule(5, 0, 10000, S, "Essence a son spends to give a community a dish of its own")


@dataclass(frozen=True)
class DeclineRules:
    onset_pct: int = rule(75, 1, 100, B, "Share of a mortal's lifespan from which the mind may begin to fail (%)")
    chance_pct: int = rule(6, 0, 100, B, "Chance each epoch a mortal past the onset age begins to decline (%)")
    reserve_pct: int = rule(50, 0, 100, B, "Share of that chance a lifetime of full education turns aside (%)")
    head_pct: int = rule(200, 100, 1000, B, "Chance of decline for a mortal whose head bears a wound that harmed the nerves (%)")
    care_pct: int = rule(50, 0, 100, B, "Chance of decline and of its worsening where a hospital, apothecary or asylum cares for the mortal (%)")
    progress_pct: int = rule(25, 0, 100, B, "Chance each epoch a declining mind worsens by a step (%)")
    memory_fade: int = rule(2, 0, 100, B, "Strength a declining mortal's memories lose each epoch for each step of severity")
    teach_block: int = rule(3, 1, 5, B, "Severity of decline at which a mortal can no longer teach or mentor")


@dataclass(frozen=True)
class AttractionRules:
    other_pct: int = rule(70, 0, 100, H, "Weight of mortals drawn to the sexes other than their own")
    same_pct: int = rule(10, 0, 100, H, "Weight of mortals drawn to their own sex")
    any_pct: int = rule(12, 0, 100, H, "Weight of mortals drawn to every sex")
    none_pct: int = rule(8, 0, 100, H, "Weight of mortals drawn to no one")
    strength_min: int = rule(30, 0, 100, H, "Least strength of a mortal's attraction")
    strength_max: int = rule(90, 0, 100, H, "Greatest strength of a mortal's attraction")
    caste_cut_pct: int = rule(50, 0, 100, H, "Share of attraction's strength a non-breeding caste loses (%)")


@dataclass(frozen=True)
class CosmicWoundRules:
    hp_per_might: int = rule(20, 1, 10000, C, "Hit points a cosmic or outer being has for each point of its might")
    damage_pct: int = rule(100, 0, 1000, C, "Scale on the harm that reaches a cosmic or outer being's body (%)")
    heal_pct: int = rule(10, 0, 100, C, "Share of its hit points a cosmic or outer being regains each epoch (%)")
    bound_heal_pct: int = rule(50, 0, 100, C, "Share of that healing a bound being keeps (%)")
    army_wound: int = rule(5, 0, 1000, C, "Harm an army deals to an incursion for each thousand soldiers it sends")
    banish_wound: int = rule(40, 0, 1000, C, "Harm a banishing deals to the banished being")
    bind_wound: int = rule(10, 0, 1000, C, "Harm a binding deals to the bound being")
    roam_floor: int = rule(30, 0, 100, C, "Mobility below which a wounded being can no longer cross between galaxies or dimensions")
    sight_floor: int = rule(30, 0, 100, C, "Sight below which a wounded being can no longer find a world to reach")
    strike_essence: int = rule(25, 0, 10000, C, "Essence a son spends for each point of force in a strike on a cosmic or outer being")
    strike_harm: int = rule(30, 0, 10000, C, "Harm a son's strike deals to a cosmic or outer being for each point of force")
