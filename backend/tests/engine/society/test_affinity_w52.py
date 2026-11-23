from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.disease import ClimateMoisture, ClimateWarmth
from aerona.domain.enums.environment import RiverClass, TemperatureBand
from aerona.engine.disease.emergence import affinity_of
from aerona.engine.disease.outbreaks import climate_fit
from aerona.rules.registry import Rules

RULES = Rules()


def land(band: TemperatureBand, *, wetland: int, rainfall: int) -> RegionEnvironmentRow:
    return RegionEnvironmentRow(
        river_class=RiverClass.NONE, wetland=wetland, temperature_band=band, rainfall=rainfall, magic_density=0, scars={}, disease_load=0
    )


def profile(warmth: ClimateWarmth, moisture: ClimateMoisture) -> DiseaseProfileRow:
    return DiseaseProfileRow(primary_route=Transmission.BITE, affinity_warmth=warmth, affinity_moisture=moisture)


def test_a_sickness_spreads_fastest_where_both_axes_fit_and_slowest_where_neither_does() -> None:
    marsh = land(TemperatureBand.HOT, wetland=90, rainfall=90)
    desert = land(TemperatureBand.FROZEN, wetland=0, rainfall=0)
    fever = profile(ClimateWarmth.WARM, ClimateMoisture.WET)
    assert climate_fit(RULES, fever, marsh) == RULES.disease.affinity_fit_pct / 100
    assert climate_fit(RULES, fever, desert) == RULES.disease.affinity_misfit_pct / 100
    half = climate_fit(RULES, profile(ClimateWarmth.WARM, ClimateMoisture.ANY), marsh)
    assert half == climate_fit(RULES, fever, marsh)
    assert climate_fit(RULES, profile(ClimateWarmth.ANY, ClimateMoisture.ANY), desert) == 1.0
    mixed = climate_fit(RULES, fever, land(TemperatureBand.HOT, wetland=0, rainfall=0))
    assert climate_fit(RULES, fever, desert) < mixed < climate_fit(RULES, fever, marsh)


def test_a_new_sickness_takes_both_axes_from_its_land() -> None:
    assert affinity_of(land(TemperatureBand.HOT, wetland=90, rainfall=90)) == (ClimateWarmth.WARM, ClimateMoisture.WET)
    assert affinity_of(None) == (ClimateWarmth.ANY, ClimateMoisture.ANY)
