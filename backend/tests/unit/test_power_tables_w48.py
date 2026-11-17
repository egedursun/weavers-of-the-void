from aerona.catalog.kinds.power_costs import POWER_COSTS
from aerona.catalog.kinds.power_hazards import POWER_HAZARDS
from aerona.catalog.kinds.resistances import RESISTANCES
from aerona.constants.units import PERCENT
from aerona.domain.enums.powers import PowerCost, PowerHazard, ResistanceKind
from aerona.engine.powers.use import RESISTANCE_READERS


def test_every_cost_hazard_and_resistance_is_defined_by_data() -> None:
    assert set(POWER_COSTS) == set(PowerCost)
    assert set(POWER_HAZARDS) == set(PowerHazard)
    assert set(RESISTANCES) == set(ResistanceKind)


def test_every_resistance_reads_a_known_source_with_a_share_in_range() -> None:
    for spec in RESISTANCES.values():
        assert spec.reads in RESISTANCE_READERS
        assert 0 <= spec.share_pct <= PERCENT


def test_a_cost_that_takes_from_body_or_standing_falls_on_mortals_only() -> None:
    assert all(POWER_COSTS[cost].mortals_only for cost in (PowerCost.LIFESPAN, PowerCost.TIME, PowerCost.RENOWN, PowerCost.BELIEF, PowerCost.OATH_STANDING))
    assert POWER_COSTS[PowerCost.SURROUNDINGS].draws == "surroundings"


def test_a_spilled_hazard_is_left_to_its_caller_to_tell() -> None:
    assert not POWER_HAZARDS[PowerHazard.LEAK].noted
    assert not POWER_HAZARDS[PowerHazard.DEPLETION].noted
    assert POWER_HAZARDS[PowerHazard.WARPING].harm == "mutate"
