from dataclasses import replace

import pytest

from aerona.catalog import commodities
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.society import Commodity
from aerona.engine.economy.household import diet_demand
from aerona.engine.economy.stocks import aggregate_need, nourishment_need
from aerona.rules.registry import Rules


def test_a_people_needs_the_same_nourishment_however_many_foods_its_world_holds(monkeypatch: pytest.MonkeyPatch) -> None:
    rules = Rules()
    before = (nourishment_need(rules, 1000), aggregate_need(rules, 1000, Commodity.FOOD))
    assert before[0] == rules.consumption.nourishment_per_1000
    widened = dict(commodities.COMMODITIES)
    widened[CommodityKind.HERBS] = replace(widened[CommodityKind.HERBS], nourishment=20, aggregate=Commodity.FOOD)
    monkeypatch.setattr(commodities, "COMMODITIES", widened)
    monkeypatch.setattr("aerona.engine.economy.stocks.COMMODITIES", widened)
    assert (nourishment_need(rules, 1000), aggregate_need(rules, 1000, Commodity.FOOD)) == before


def test_a_people_asks_its_meals_for_exactly_the_nourishment_it_needs() -> None:
    rules = Rules()
    need = nourishment_need(rules, 1000)
    for staples in ((), (CommodityKind.FISH,)):
        wanted = diet_demand(rules, 1000, staples, need)
        asked = sum(amount * commodities.COMMODITIES[kind].nourishment for kind, amount in wanted.items())
        assert abs(asked - need) <= len(wanted) * 15
