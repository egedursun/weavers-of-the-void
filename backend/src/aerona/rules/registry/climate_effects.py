from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ClimateEffectsRules:
    temperate_fertility: int = rule(1, -50, 50, RuleGroup.POPULATION_AND_GROWTH, "Temperate age: fertility change per epoch")
    temperate_weight: int = rule(40, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the temperate age occurring")
    drought_century_fertility: int = rule(-5, -50, 50, RuleGroup.POPULATION_AND_GROWTH, "Drought century: fertility change per epoch")
    drought_century_weight: int = rule(18, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the drought century occurring")
    rain_age_fertility: int = rule(4, -50, 50, RuleGroup.POPULATION_AND_GROWTH, "Rain age: fertility change per epoch")
    rain_age_weight: int = rule(18, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the rain age occurring")
    ice_age_fertility: int = rule(-4, -50, 50, RuleGroup.POPULATION_AND_GROWTH, "Ice age: fertility change per epoch")
    ice_age_weight: int = rule(12, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the ice age occurring")
    scorching_age_fertility: int = rule(-3, -50, 50, RuleGroup.POPULATION_AND_GROWTH, "Scorching age: fertility change per epoch")
    scorching_age_weight: int = rule(12, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the scorching age occurring")
    ice_age_population_loss: int = rule(3, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Ice age: population loss per epoch (%)")
    scorching_age_plague_freq: int = rule(150, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Scorching age: plague frequency (%)")
    first_duration: int = rule(3, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Base duration of the first climate age (epochs)")
    first_die: int = rule(3, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Die added to the first climate age (epochs)")
    duration: int = rule(3, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Base duration of a climate age (epochs)")
    duration_die: int = rule(4, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Die added to a climate age (epochs)")
    coast_drought_divisor: int = rule(2, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Drought strikes the coast divided by this number")
    coast_rain_bonus: int = rule(1, 0, 50, RuleGroup.POPULATION_AND_GROWTH, "Extra fertility of the coast in a rain age")
    mountain_ice_loss: int = rule(3, 0, 50, RuleGroup.POPULATION_AND_GROWTH, "Extra fertility loss of mountainous regions in an ice age")
    fertility_equilibrium: int = rule(50, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Equilibrium value fertility is drawn to in the long run")
    fertility_recovery_divisor: int = rule(8, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Rate at which depleted land returns to 50 (divisor)")
    fertility_decline_divisor: int = rule(
        10,
        1,
        200,
        RuleGroup.POPULATION_AND_GROWTH,
        "Rate at which fertile land declines to 50 (divisor; balanced by climate push: ~60 in temperate age, ~90 in rain age)",
    )
    bounty_law_fertility: int = rule(3, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Per-epoch fertility gain of lands under the bounty law")
    drought_law_fertility: int = rule(3, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Per-epoch fertility loss of lands under the drought law")
