from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.geology import DeepPassageKind, DeepPassageState, UndergroundStratum
from aerona.engine.primitives.deep import DeepEdge, LayeredGraph, passage_kind, shape_fault
from aerona.rules.registry import Rules

RULES = Rules()
U = UndergroundStratum
FOOT = frozenset({MovementMode.ON_FOOT})
SUBMERGED = frozenset({MovementMode.SUBMERGED})


def graph(*edges: DeepEdge) -> LayeredGraph:
    land = {1: [2], 2: [1]}
    return LayeredGraph(lambda region: land.get(region, []), edges, narrow_width=RULES.underground.narrow_width, vertical_cost=1)


def opening(state: DeepPassageState = DeepPassageState.OPEN, width: int = 60) -> DeepEdge:
    return DeepEdge((1, None), (1, U.CAVERN_UPPER), state, width, DeepPassageKind.OPENING)


def test_a_cell_below_is_reached_only_through_its_passages() -> None:
    assert graph().hops((2, None), (1, U.CAVERN_UPPER)) is None
    assert graph(opening()).hops((2, None), (1, U.CAVERN_UPPER)) == 2
    assert graph(opening(DeepPassageState.COLLAPSED)).hops((1, None), (1, U.CAVERN_UPPER), FOOT) is None
    assert graph(opening(DeepPassageState.FLOODED)).hops((1, None), (1, U.CAVERN_UPPER), SUBMERGED) == 1
    assert graph(opening(DeepPassageState.FLOODED)).hops((1, None), (1, U.CAVERN_UPPER), FOOT) is None
    assert graph(opening(width=5)).hops((1, None), (1, U.CAVERN_UPPER), frozenset({MovementMode.WHEELED})) is None


def test_only_three_shapes_of_passage_exist() -> None:
    assert passage_kind((1, U.CAVERN_UPPER), (2, U.CAVERN_UPPER)) is DeepPassageKind.LEVEL
    assert passage_kind((1, U.CAVERN_UPPER), (1, U.CAVERN_LOWER)) is DeepPassageKind.VERTICAL
    assert passage_kind((1, None), (1, U.AQUIFER)) is DeepPassageKind.OPENING
    assert shape_fault((1, None), (2, U.CAVERN_UPPER), True) is not None
    assert shape_fault((1, U.CAVERN_UPPER), (2, U.CAVERN_LOWER), True) is not None
    assert shape_fault((1, U.CAVERN_UPPER), (3, U.CAVERN_UPPER), False) is not None
    assert shape_fault((1, U.CAVERN_UPPER), (2, U.CAVERN_UPPER), True) is None
