from aerona.domain.enums.economy import HazardKind
from aerona.engine.economy.extraction import hazard_chance
from aerona.rules.registry import Rules


def test_every_hazard_has_a_chance_at_works_of_full_difficulty() -> None:
    rules = Rules()
    assert all(hazard_chance(rules, kind, 100, 0) > 0 for kind in HazardKind)
