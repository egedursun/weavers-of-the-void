from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ClimateEffectsRules:
    temperate_temperature: int = rule(0, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Temperate age: temperature shift")
    temperate_rain: int = rule(0, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Temperate age: rainfall shift")
    temperate_weight: int = rule(40, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the temperate age occurring")
    warming_temperature: int = rule(6, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Warming age: temperature shift")
    warming_rain: int = rule(0, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Warming age: rainfall shift")
    warming_weight: int = rule(15, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the warming age occurring")
    cooling_temperature: int = rule(-6, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Cooling age: temperature shift")
    cooling_rain: int = rule(0, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Cooling age: rainfall shift")
    cooling_weight: int = rule(15, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the cooling age occurring")
    strong_phase_pct: int = rule(15, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Chance an oscillation turns to its strong phase, doubling its effect (%)")
    drought_century_temperature: int = rule(6, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Drought century: temperature shift")
    drought_century_rain: int = rule(-25, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Drought century: rainfall shift")
    drought_century_weight: int = rule(18, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the drought century occurring")
    rain_age_temperature: int = rule(-2, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Rain age: temperature shift")
    rain_age_rain: int = rule(22, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Rain age: rainfall shift")
    rain_age_weight: int = rule(18, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the rain age occurring")
    ice_age_temperature: int = rule(-22, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Ice age: temperature shift")
    ice_age_rain: int = rule(-8, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Ice age: rainfall shift")
    ice_age_weight: int = rule(12, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the ice age occurring")
    scorching_age_temperature: int = rule(18, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Scorching age: temperature shift")
    scorching_age_rain: int = rule(-12, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Scorching age: rainfall shift")
    scorching_age_weight: int = rule(12, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the scorching age occurring")
    hothouse_temperature: int = rule(28, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Hothouse age: temperature shift")
    hothouse_rain: int = rule(15, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Hothouse age: rainfall shift")
    hothouse_weight: int = rule(4, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the hothouse age occurring")
    snowball_temperature: int = rule(-40, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Snowball age: temperature shift")
    snowball_rain: int = rule(-30, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Snowball age: rainfall shift")
    snowball_weight: int = rule(2, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the snowball age occurring")
    variable_temperature: int = rule(0, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Variable age: mean temperature shift")
    variable_rain: int = rule(0, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Variable age: mean rainfall shift")
    variable_epochs: int = rule(
        1, 1, 20, RuleGroup.POPULATION_AND_GROWTH, "Most epochs a variable age lasts before the next age is drawn, so the climate swings"
    )
    variable_weight: int = rule(10, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the variable age occurring")
    wet_cold_temperature: int = rule(-12, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Wet and cold age: temperature shift")
    wet_cold_rain: int = rule(18, -100, 100, RuleGroup.POPULATION_AND_GROWTH, "Wet and cold age: rainfall shift")
    wet_cold_weight: int = rule(10, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Weight of the wet and cold age occurring")
    ice_age_population_loss: int = rule(3, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Ice age: population loss per epoch (%)")
    scorching_age_plague_freq: int = rule(150, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Scorching age: plague frequency (%)")
    first_duration: int = rule(3, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Base duration of the first climate age (epochs)")
    compounding_damping_pct: int = rule(
        200,
        0,
        1000,
        RuleGroup.POPULATION_AND_GROWTH,
        "How strongly a world already pushed cold or hot by its sky resists an age that pushes it further the same way (%)",
    )
    first_die: int = rule(3, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Die added to the first climate age (epochs)")
    duration: int = rule(3, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Base duration of a climate age (epochs)")
    duration_die: int = rule(4, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Die added to a climate age (epochs)")
    coast_drought_divisor: int = rule(2, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Rainfall loss of a drought century on the coast is divided by this number")
    coast_rain_bonus: int = rule(6, 0, 50, RuleGroup.POPULATION_AND_GROWTH, "Extra rainfall of the coast in a rain age")
    mountain_ice_loss: int = rule(8, 0, 50, RuleGroup.POPULATION_AND_GROWTH, "Extra cold of mountainous regions in an ice age")
    fertility_recovery_divisor: int = rule(8, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Rate at which depleted soil returns to its natural fertility (divisor)")
    fertility_decline_divisor: int = rule(
        10, 1, 200, RuleGroup.POPULATION_AND_GROWTH, "Rate at which enriched soil falls back to its natural fertility (divisor)"
    )
    bounty_law_fertility: int = rule(15, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Extra fertility lands under the bounty law enjoy while the law holds (%)")
    drought_law_fertility: int = rule(15, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Fertility lands under the drought law lose while the law holds (%)")
