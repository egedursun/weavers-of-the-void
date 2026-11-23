from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

F = RuleGroup.FATE_AND_CHRONICLE


@dataclass(frozen=True)
class StorytellerRules:
    tension_scale: int = rule(400, 1, 100000, F, "Summed weight of one epoch's strife and harm that fills the tension meter")
    tension_carry_pct: int = rule(40, 0, 100, F, "Share of last epoch's tension that carries into the next (%)")
    steady_target: int = rule(45, 0, 100, F, "Tension a steady storyteller aims for")
    palette_late_frost_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a late frost or an ice storm when it leans toward it")
    palette_long_season_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a long season setting in when it leans toward it")
    palette_land_shift_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a river shifting or the land changing when it leans toward it")
    palette_upwelling_failure_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives the sea's upwelling failing when it leans toward it")
    palette_swarm_strike_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a swarm striking or herds going feral when it leans toward it")
    palette_keystone_loss_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a keystone kind lost when it leans toward it")
    palette_beast_woken_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a beast woken when it leans toward it")
    palette_ruler_gangrene_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a wound turning to gangrene when it leans toward it")
    palette_fortune_curse_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a charm or a turn of fortune when it leans toward it")
    palette_grief_vengeance_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives grief turning to vengeance when it leans toward it")
    palette_boycott_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a boycott when it leans toward it")
    palette_route_season_closed_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a route closed by its season when it leans toward it")
    palette_impact_strike_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a body from the sky striking a world when it leans toward it")
    palette_fair_held_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a fair held when it leans toward it")
    palette_seasons_settled_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives the seasons settling when it leans toward it")
    palette_sanitation_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives sanitation ordered when it leans toward it")
    palette_relief_given_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives relief given when it leans toward it")
    palette_crisis_mediated_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a crisis or a treaty mediated when it leans toward it")
    palette_gift_released_weight: int = rule(10, 0, 100, F, "Tension weight the storyteller gives a gift debt released when it leans toward it")
    rising_start: int = rule(25, 0, 100, F, "Tension a rising storyteller aims for at the dawn of the world")
    rising_step: int = rule(2, 0, 100, F, "Tension a rising storyteller adds to its aim each epoch")
    rising_cap: int = rule(85, 0, 100, F, "Highest tension a rising storyteller aims for")
    cyclic_middle: int = rule(45, 0, 100, F, "Middle of a cyclic storyteller's wave")
    cyclic_amplitude: int = rule(30, 0, 100, F, "Height of a cyclic storyteller's wave above and below its middle")
    cyclic_period: int = rule(8, 2, 1000, F, "Epochs of one full wave of golden age and crisis")
    chaotic_low: int = rule(10, 0, 100, F, "Lowest tension a chaotic storyteller may aim for")
    chaotic_high: int = rule(90, 0, 100, F, "Highest tension a chaotic storyteller may aim for")
    band: int = rule(12, 0, 100, F, "Distance from the aim within which tension counts as on course")
    boost_max_pct: int = rule(50, 0, 100, F, "Most the storyteller raises or lowers spontaneous disruptions (%)")
    boost_per_point_pct: int = rule(3, 0, 100, F, "Change to spontaneous rates for each point of tension off course (%)")
    palette_rest_pct: int = rule(30, 0, 300, F, "Most the storyteller raises the chances of events from a subsystem that has not acted lately (%)")
    palette_lean_pct: int = rule(
        100, 0, 1000, F, "How far a quiet world leans toward disruptions and a heated one toward recoveries, per point of an event's weight (%)"
    )
    variety_window: int = rule(4, 1, 100, F, "Epochs the storyteller remembers which kinds of disruption struck")
    variety_pct: int = rule(40, 0, 100, F, "Most a recently repeated kind of disruption is made less likely (%)")
    variety_decay_pct: int = rule(50, 0, 100, F, "Share of a disruption kind's recent count forgotten each epoch (%)")
    spotlight_weight_pct: int = rule(200, 100, 1000, F, "Weight a spotlighted record gets when agents and the chronicler choose whom to follow (%)")
    spotlight_min_importance: int = rule(20, 0, 100, F, "Importance a record needs to be spotlighted")
    harvest_gift: int = rule(15, 0, 100, F, "Harvest a heated world's hardest pressed community is given when the storyteller calls a recovery")
    revival_band: int = rule(1, 0, 1, F, "Let the storyteller decide when a quiet world is revived (1) or revive by the world balance alone (0)")
