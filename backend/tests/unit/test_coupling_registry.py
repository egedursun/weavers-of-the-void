from itertools import permutations

from aerona.engine.interconnect.edges import matrix, structural_edges
from aerona.engine.interconnect.registry import Subsystem

INTENTIONALLY_EMPTY: frozenset[tuple[Subsystem, Subsystem]] = frozenset()


def test_every_ordered_pair_of_subsystems_is_coupled_or_declared_empty() -> None:
    coupled = set(matrix()) | {(edge.source, edge.target) for edge in structural_edges() if edge.source is not edge.target}
    pairs = set(permutations(Subsystem, 2))
    assert sorted((a.value, b.value) for a, b in pairs - coupled - INTENTIONALLY_EMPTY) == []
    assert sorted((a.value, b.value) for a, b in INTENTIONALLY_EMPTY & coupled) == []
