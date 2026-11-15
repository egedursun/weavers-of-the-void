from types import SimpleNamespace
from typing import Any, cast

from aerona.domain.enums.industry import EnergyKind
from aerona.engine.economy.book import EconomyBook
from aerona.engine.industry.energy import own_hands, scale_by_energy, worked_by_hand
from aerona.rules.registry import Rules


def spent_town() -> EconomyBook:
    row = SimpleNamespace(muscle=0, water=0, wind=0, heat=0, magic=0, divine=0, spent={}, short={})
    return cast(EconomyBook, cast(Any, SimpleNamespace(industry={1: row}, magic_heat_pct=0)))


def test_farmers_work_their_own_fields_when_the_town_s_muscle_is_spent_elsewhere() -> None:
    rules = Rules()
    need = own_hands(rules, 1000)
    assert scale_by_energy(spent_town(), 1, EnergyKind.MUSCLE, need) == 0.0
    assert worked_by_hand(spent_town(), rules, 1, EnergyKind.MUSCLE, need=need, workers=1000) == 1.0
    assert worked_by_hand(spent_town(), rules, 1, EnergyKind.MUSCLE, need=need * 2, workers=1000) == 0.5
    assert worked_by_hand(spent_town(), rules, 1, EnergyKind.WIND, need=need, workers=1000) == 0.0
