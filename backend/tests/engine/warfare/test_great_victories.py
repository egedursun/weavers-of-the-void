from types import SimpleNamespace
from typing import cast

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import ArmyStats
from aerona.engine.military.battle import Side
from aerona.engine.phases.warfare import crushing, routed_side
from aerona.rules.registry import Rules


def beaten(fielded: int, lost: int, captives: int = 0) -> Side:
    return cast(Side, SimpleNamespace(stacks=[SimpleNamespace(start=fielded, lost=lost)], captives=captives))


def test_a_win_is_great_only_when_the_beaten_side_lost_a_real_share_of_its_soldiers() -> None:
    rules = Rules()
    assert not crushing(rules, beaten(1200, 4))
    assert crushing(rules, beaten(1200, 400))
    assert crushing(rules, beaten(10, 4))
    assert crushing(rules, beaten(100, 5, captives=20))
    assert not crushing(rules, None)


def test_a_win_where_the_victor_bled_more_than_the_beaten_is_never_great() -> None:
    rules = Rules()
    assert not crushing(rules, beaten(30, 23), beaten(1200, 897))
    assert not crushing(rules, beaten(60, 42), beaten(1500, 915))
    assert not crushing(rules, beaten(20, 11), beaten(12, 7))
    assert crushing(rules, beaten(60, 41), beaten(900, 3))


def army(size: int, morale: int) -> tuple[EntityRow, ArmyRow]:
    return EntityRow(entity_type=EntityType.ARMY, stats=ArmyStats(size=size, morale=morale)), cast(ArmyRow, None)


def test_a_side_ahead_in_the_war_is_never_counted_routed_for_its_small_army() -> None:
    campaigns = Rules().campaigns
    armies = {1: army(campaigns.disband_soldiers - 1, 80), 2: army(campaigns.disband_soldiers + 500, 80)}
    assert routed_side(campaigns, 2, (1, 2), armies) is None
    assert routed_side(campaigns, -2, (1, 2), armies) == 1
    assert routed_side(campaigns, 0, (1, 2), armies) == 1
