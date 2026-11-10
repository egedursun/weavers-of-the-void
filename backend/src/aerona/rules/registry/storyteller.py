from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

F = RuleGroup.FATE_AND_CHRONICLE


@dataclass(frozen=True)
class StorytellerRules:
    tension_scale: int = rule(400, 1, 100000, F, "Summed incident weight of one epoch that fills the tension meter")
    tension_carry_pct: int = rule(40, 0, 100, F, "Share of last epoch's tension that carries into the next (%)")
    steady_target: int = rule(45, 0, 100, F, "Tension a steady storyteller aims for")
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
    variety_window: int = rule(4, 1, 100, F, "Epochs the storyteller remembers which kinds of disruption struck")
    variety_pct: int = rule(40, 0, 100, F, "Most a recently repeated kind of disruption is made less likely (%)")
    variety_decay_pct: int = rule(50, 0, 100, F, "Share of a disruption kind's recent count forgotten each epoch (%)")
    spotlight_weight_pct: int = rule(200, 100, 1000, F, "Weight a spotlighted record gets when agents and the chronicler choose whom to follow (%)")
    spotlight_min_importance: int = rule(20, 0, 100, F, "Importance a record needs to be spotlighted")
    harvest_gift: int = rule(15, 0, 100, F, "Harvest a heated world's hardest pressed community is given when the storyteller calls a recovery")
    revival_band: int = rule(1, 0, 1, F, "Let the storyteller decide when a quiet world is revived (1) or revive by the world balance alone (0)")
