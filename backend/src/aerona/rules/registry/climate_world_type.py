from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ClimateWorldTypeRules:
    ocean_ice_age: int = rule(25, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Ocean world: ice-age weight (%)")
    ocean_drought: int = rule(30, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Ocean world: drought weight (%)")
    ocean_rain: int = rule(200, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Ocean world: rain-age weight (%)")
    sand_drought: int = rule(250, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Sand world: drought weight (%)")
    sand_rain: int = rule(30, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Sand world: rain-age weight (%)")
    sand_scorching: int = rule(180, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Sand world: scorching-age weight (%)")
    ice_ice_age: int = rule(300, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Ice world: ice-age weight (%)")
    ice_scorching: int = rule(20, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Ice world: scorching-age weight (%)")
    ice_drought: int = rule(60, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Ice world: drought weight (%)")
    lava_scorching: int = rule(300, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Lava world: scorching-age weight (%)")
    lava_ice_age: int = rule(10, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Lava world: ice-age weight (%)")
    lava_rain: int = rule(40, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Lava world: rain-age weight (%)")
    gas_rain: int = rule(150, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Gas world: rain-age weight (%)")
    dead_temperate: int = rule(150, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Dead world: temperate-age weight (%)")
    dead_rain: int = rule(50, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Dead world: rain-age weight (%)")
    tidally_locked_scorching: int = rule(200, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Tidally locked world: scorching-age weight (%)")
    tidally_locked_ice_age: int = rule(200, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Tidally locked world: ice-age weight (%)")
    tidally_locked_temperate: int = rule(50, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Tidally locked world: temperate-age weight (%)")
    generation_ship_temperate: int = rule(400, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Generation ship: temperate-age weight (%)")
    void_pocket_temperate: int = rule(300, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Void pocket: temperate-age weight (%)")
    corpse_world_drought: int = rule(180, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Corpse world: drought weight (%)")
    corpse_world_rain: int = rule(40, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Corpse world: rain-age weight (%)")
    living_rain: int = rule(150, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Living world: rain-age weight (%)")
    crystal_ice_age: int = rule(150, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Crystal world: ice-age weight (%)")
    asteroid_belt_drought: int = rule(200, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Asteroid belt: drought weight (%)")
    ringed_rain: int = rule(130, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Ringed world: rain-age weight (%)")
    gods_palace_temperate: int = rule(300, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "God's palace: temperate-age weight (%)")
