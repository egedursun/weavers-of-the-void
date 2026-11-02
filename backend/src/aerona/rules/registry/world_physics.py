from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class WorldPhysicsRules:
    time_factor_min: int = rule(
        25,
        1,
        10000,
        RuleGroup.COSMOS_AND_TRAVEL,
        "Minimum time factor Fate gives a world it births (%; 100 = normal; does not limit a value the god sets manually)",
    )
    time_factor_max: int = rule(
        400, 1, 10000, RuleGroup.COSMOS_AND_TRAVEL, "Maximum time factor Fate gives a world it births (%; does not limit a value the god sets manually)"
    )
    capacity_no_atmosphere: int = rule(25, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a world without atmosphere (%)")
    capacity_thin: int = rule(60, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a world with thin atmosphere (%)")
    capacity_normal: int = rule(100, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a world with normal atmosphere (%)")
    capacity_dense: int = rule(115, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a world with dense atmosphere (%)")
    capacity_toxic: int = rule(40, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a world with toxic atmosphere (%)")
    martiality_low_gravity: int = rule(-4, -100, 100, RuleGroup.COSMOS_AND_TRAVEL, "Martiality effect in low gravity")
    martiality_normal_gravity: int = rule(0, -100, 100, RuleGroup.COSMOS_AND_TRAVEL, "Martiality effect in normal gravity")
    martiality_high_gravity: int = rule(6, -100, 100, RuleGroup.COSMOS_AND_TRAVEL, "Martiality effect in high gravity")
    ringed_capacity: int = rule(90, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a ringed world (%; ring shadows shorten the growing season)")
    ringed_route_danger: int = rule(5, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Extra danger of a route touching a ringed world (ring debris)")
    asteroid_belt_capacity: int = rule(50, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of an asteroid belt (%)")
    asteroid_belt_route_danger: int = rule(10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Extra danger of a route touching an asteroid belt (drifting rocks)")
    tidally_locked_capacity: int = rule(80, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a tidally locked world (%; only the twilight band is mild)")
    void_pocket_capacity: int = rule(60, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a void pocket (%)")
    void_pocket_leak: int = rule(3, 0, 50, RuleGroup.COSMIC_HORROR, "Leak a void pocket draws in from outside each epoch")
    void_pocket_sanity_erosion: int = rule(2, 0, 100, RuleGroup.COSMIC_HORROR, "Extra per-epoch sanity loss of those living in a void pocket")
    gods_palace_capacity: int = rule(120, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of the god's palace (%)")
    gods_palace_leak_repair: int = rule(2, 0, 50, RuleGroup.COSMIC_HORROR, "Per-epoch leak repair of the god's palace (its walls keep the outside away)")
    generation_ship_capacity: int = rule(70, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a generation ship (%)")
    generation_ship_drift_epochs: int = rule(
        10, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "A generation ship moves on to another star every this many epochs (0 off)"
    )
    corpse_world_capacity: int = rule(90, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a corpse-world (%)")
    corpse_world_leak: int = rule(1, 0, 50, RuleGroup.COSMIC_HORROR, "Leak seeping from the dead god's wounds into a corpse-world each epoch")
    corpse_world_fertility_decay: int = rule(
        1, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Per-epoch fertility loss of the regions of a corpse-world as the body rots"
    )
    forge_capacity: int = rule(85, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a forge-world (%; soot and slag crowd the fields)")
    forge_fertility_decay: int = rule(
        1, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Per-epoch fertility loss of the regions of a forge-world as soot settles on them"
    )
    forge_ore_yield: int = rule(
        160, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ore a community of a forge-world draws from its ore resources (%; 100 = as elsewhere)"
    )
    super_earth_capacity: int = rule(110, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a super-earth (%)")
    super_earth_earthquake_pct: int = rule(150, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Super-earth: chance of a natural earthquake (% of the usual)")
    ice_giant_capacity: int = rule(35, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a ice giant (%)")
    ice_giant_storm_pct: int = rule(200, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ice giant: chance of a natural storm (% of the usual)")
    hot_giant_capacity: int = rule(20, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a hot giant (%)")
    hot_giant_route_danger: int = rule(5, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Extra danger of a route touching a hot giant")
    hot_giant_storm_pct: int = rule(250, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Hot giant: chance of a natural storm (% of the usual)")
    iron_capacity: int = rule(55, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a iron world (%)")
    iron_ore_yield: int = rule(
        200, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ore a community of a iron world draws from its ore resources (%; 100 = as elsewhere)"
    )
    iron_earthquake_pct: int = rule(120, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Iron world: chance of a natural earthquake (% of the usual)")
    iron_storm_pct: int = rule(50, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Iron world: chance of a natural storm (% of the usual)")
    carbon_capacity: int = rule(60, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a diamond world (%)")
    carbon_ore_yield: int = rule(
        80, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ore a community of a diamond world draws from its ore resources (%; 100 = as elsewhere)"
    )
    carbon_earthquake_pct: int = rule(120, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Diamond world: chance of a natural earthquake (% of the usual)")
    greenhouse_capacity: int = rule(30, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a greenhouse world (%)")
    greenhouse_fertility_decay: int = rule(1, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Per-epoch fertility loss of the regions of a greenhouse world")
    greenhouse_drought_pct: int = rule(250, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Greenhouse world: chance of a natural drought (% of the usual)")
    greenhouse_storm_pct: int = rule(50, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Greenhouse world: chance of a natural storm (% of the usual)")
    dwarf_planet_capacity: int = rule(40, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a dwarf world (%)")
    dwarf_planet_ore_yield: int = rule(
        70, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ore a community of a dwarf world draws from its ore resources (%; 100 = as elsewhere)"
    )
    dwarf_planet_storm_pct: int = rule(0, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Dwarf world: chance of a natural storm (% of the usual)")
    dwarf_planet_flood_pct: int = rule(0, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Dwarf world: chance of a natural flood (% of the usual)")
    chthonian_capacity: int = rule(20, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a chthonian world (%)")
    chthonian_ore_yield: int = rule(
        180, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ore a community of a chthonian world draws from its ore resources (%; 100 = as elsewhere)"
    )
    chthonian_earthquake_pct: int = rule(250, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Chthonian world: chance of a natural earthquake (% of the usual)")
    hycean_capacity: int = rule(90, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a steam-ocean world (%)")
    hycean_storm_pct: int = rule(200, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Steam-ocean world: chance of a natural storm (% of the usual)")
    hycean_flood_pct: int = rule(150, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Steam-ocean world: chance of a natural flood (% of the usual)")
    jungle_capacity: int = rule(120, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a jungle world (%)")
    jungle_plague_pct: int = rule(150, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Jungle world: chance of a natural plague (% of the usual)")
    jungle_flood_pct: int = rule(150, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Jungle world: chance of a natural flood (% of the usual)")
    fungal_capacity: int = rule(95, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a fungal world (%)")
    fungal_sanity_erosion: int = rule(1, 0, 100, RuleGroup.COSMIC_HORROR, "Extra per-epoch sanity loss of those living on a fungal world")
    fungal_plague_pct: int = rule(200, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Fungal world: chance of a natural plague (% of the usual)")
    shattered_capacity: int = rule(70, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a shattered world (%)")
    shattered_route_danger: int = rule(8, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Extra danger of a route touching a shattered world")
    shattered_leak: int = rule(1, 0, 50, RuleGroup.COSMIC_HORROR, "Leak a shattered world draws in from outside each epoch")
    shattered_ore_yield: int = rule(
        130, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ore a community of a shattered world draws from its ore resources (%; 100 = as elsewhere)"
    )
    shattered_earthquake_pct: int = rule(200, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Shattered world: chance of a natural earthquake (% of the usual)")
    hollow_capacity: int = rule(100, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a hollow world (%)")
    hollow_leak_repair: int = rule(1, 0, 50, RuleGroup.COSMIC_HORROR, "Per-epoch leak repair of a hollow world (its shell keeps the outside away)")
    hollow_earthquake_pct: int = rule(50, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Hollow world: chance of a natural earthquake (% of the usual)")
    ice_shell_capacity: int = rule(45, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a ice-shell world (%)")
    ice_shell_earthquake_pct: int = rule(150, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ice-shell world: chance of a natural earthquake (% of the usual)")
    ice_shell_storm_pct: int = rule(30, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ice-shell world: chance of a natural storm (% of the usual)")
    methane_capacity: int = rule(35, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Life capacity of a methane world (%)")
    methane_flood_pct: int = rule(150, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Methane world: chance of a natural flood (% of the usual)")
    forge_earthquake_pct: int = rule(150, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Forge-world: chance of a natural earthquake (% of the usual)")
    corpse_world_plague_pct: int = rule(150, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Corpse-world: chance of a natural plague (% of the usual)")
    lava_earthquake_pct: int = rule(200, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Lava world: chance of a natural earthquake (% of the usual)")
    ocean_storm_pct: int = rule(150, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ocean world: chance of a natural storm (% of the usual)")
    living_earthquake_pct: int = rule(150, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Living world: chance of a natural earthquake (% of the usual)")
    artificial_earthquake_pct: int = rule(
        0, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Chance of an earthquake on an artificial world (palace, ship; % of the usual)"
    )
