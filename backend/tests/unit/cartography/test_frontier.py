import math

from aerona.cartography.frontier import frontier_position
from tests.unit.cartography.helpers import RULES


def test_frontier_position_keeps_the_exploration_distance_and_seeks_room() -> None:
    x, y = frontier_position((1000.0, 1000.0), [(1300.0, 1000.0)], lambda: 0.0, RULES)
    assert abs(math.hypot(x - 1000, y - 1000) - RULES.exploration.map_distance) <= 1
    assert x < 1000


def test_frontier_position_without_neighbours_uses_the_first_direction() -> None:
    assert frontier_position((0.0, 0.0), [], lambda: 0.0, RULES) == (RULES.exploration.map_distance, 0)
