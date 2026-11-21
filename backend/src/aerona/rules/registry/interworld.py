from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class InterworldRules(Spanned):
    transit_loss_pct: int = rule(5, 0, 100, S, "Share of a campaign's forces lost in each epoch of transit (%)")
    supply_decay_per_hop: int = rule(10, 0, 100, S, "Supply a landed force loses each epoch for each epoch its line takes, unless its side holds the orbit")
    landing_needs_control_pct: int = rule(60, 0, 100, S, "Orbital control a campaign needs before it can land (%)")
    bombard_harm_per_strength: int = rule(2, 0, 50, S, "People of a bombarded town killed for each point of orbital control, in tenths of a percent")
    migration_push_threshold: int = rule(60, 0, 100, S, "Push at which a community begins to move to another world")
    carrier_people_per_capacity: int = rule(100, 1, 100000, S, "People or soldiers one carrier, or one point of a route's capacity, brings across in an epoch")
    campaign_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a realm at war with a realm on another world sends a campaign across (%)")
    starving_supply: int = rule(30, 0, 100, S, "Supply below which a landed force withers")
    orbit_hold_supply: int = rule(80, 0, 100, S, "Supply a landed force keeps while its side holds the orbit")
    blockade_toll_pct: int = rule(30, 0, 100, S, "Toll the holder of a world's orbit takes from the routes that reach it (%)")
    migration_share_pct: int = rule(5, 0, 100, S, "Share of a moving community that leaves in an epoch at full push (%)")
    migration_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a community under enough push begins to move (%)")
    migration_cap_pct: int = rule(50, 0, 100, S, "Share of a community that may leave in one movement before it ends (%)")
