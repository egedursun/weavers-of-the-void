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
