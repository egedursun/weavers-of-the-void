from aerona.catalog.climate import CLIMATES, climate_profile, climate_weights
from aerona.domain.enums.world import ClimateEra, WorldType
from aerona.rules.registry import Rules


def test_every_climate_age_has_a_profile_and_can_be_drawn_on_every_kind_of_world() -> None:
    rules = Rules()
    assert set(CLIMATES) == set(ClimateEra)
    for era in ClimateEra:
        profile = climate_profile(rules, era)
        assert profile.label and profile.description
    for world_type in WorldType:
        assert set(climate_weights(rules, world_type)) == set(ClimateEra)


def test_the_new_ages_push_warmth_and_rain_their_own_way() -> None:
    rules = Rules()
    assert climate_profile(rules, ClimateEra.HOTHOUSE).temperature_shift > climate_profile(rules, ClimateEra.SCORCHING).temperature_shift
    assert climate_profile(rules, ClimateEra.SNOWBALL).temperature_shift < climate_profile(rules, ClimateEra.ICE_AGE).temperature_shift
    assert climate_profile(rules, ClimateEra.WET_COLD).rain_shift > 0 > climate_profile(rules, ClimateEra.WET_COLD).temperature_shift
    assert rules.climate_effects.variable_epochs <= rules.climate_effects.duration
