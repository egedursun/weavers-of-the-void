import heapq
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from itertools import pairwise

from aerona.catalog.deep import PASSAGE_STATES
from aerona.catalog.movement import EVERY_WAY, NARROW_WAYS
from aerona.catalog.strata import STRATA
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.geology import DeepPassageKind, DeepPassageState, UndergroundStratum

Level = UndergroundStratum | None
Cell = tuple[int, Level]


@dataclass(frozen=True)
class DeepEdge:
    first: Cell
    second: Cell
    state: DeepPassageState
    width: int
    kind: DeepPassageKind


def front_cells(first: Cell, second: Cell) -> tuple[Cell, Cell]:
    low, high = sorted((first, second), key=lambda cell: (cell[0], cell[1].value if cell[1] is not None else ""))
    return low, high


def passage_kind(first: Cell, second: Cell) -> DeepPassageKind:
    if first[0] == second[0]:
        return DeepPassageKind.OPENING if first[1] is None or second[1] is None else DeepPassageKind.VERTICAL
    return DeepPassageKind.LEVEL


def shape_fault(first: Cell, second: Cell, neighbours: bool) -> str | None:
    if first == second:
        return "a passage needs two different ends"
    if first[0] == second[0]:
        return None
    if first[1] is None or second[1] is None:
        return "an opening joins a region's surface to a cell beneath that same region"
    if first[1] is not second[1]:
        return "a level passage joins the same stratum beneath two regions"
    return None if neighbours else "a level passage joins cells beneath neighbouring regions"


def cell_modes(level: Level) -> frozenset[MovementMode]:
    return EVERY_WAY if level is None else STRATA[level].modes


def edge_modes(edge: DeepEdge, narrow_width: int) -> frozenset[MovementMode]:
    passes = PASSAGE_STATES[edge.state].passes
    both = cell_modes(edge.first[1]) & cell_modes(edge.second[1])
    modes = both if passes is None else passes & (both | passes)
    return modes & NARROW_WAYS if edge.width < narrow_width else modes


class LayeredGraph:
    def __init__(self, neighbours: Callable[[int], list[int]], edges: Iterable[DeepEdge], *, narrow_width: int, vertical_cost: int) -> None:
        self._neighbours = neighbours
        self._narrow = narrow_width
        self._vertical = vertical_cost
        self._edges: dict[Cell, list[tuple[Cell, frozenset[MovementMode], int]]] = {}
        for edge in edges:
            modes = edge_modes(edge, narrow_width)
            cost = 1 if edge.kind is DeepPassageKind.LEVEL else vertical_cost
            self._edges.setdefault(edge.first, []).append((edge.second, modes, cost))
            self._edges.setdefault(edge.second, []).append((edge.first, modes, cost))

    @property
    def empty(self) -> bool:
        return not self._edges

    def steps(self, cell: Cell, modes: frozenset[MovementMode] | None) -> list[tuple[Cell, int]]:
        found: list[tuple[Cell, int]] = [((other, None), 1) for other in self._neighbours(cell[0])] if cell[1] is None else []
        for other, passes, cost in self._edges.get(cell, ()):
            if passes and (modes is None or passes & modes):
                found.append((other, cost))
        return found

    def path(self, first: Cell, second: Cell, modes: frozenset[MovementMode] | None = None, avoid: frozenset[Cell] = frozenset()) -> list[Cell] | None:
        if first == second:
            return [first]
        best: dict[Cell, int] = {first: 0}
        before: dict[Cell, Cell] = {}
        queue: list[tuple[int, int, Cell]] = [(0, 0, first)]
        order = 0
        while queue:
            cost, _, cell = heapq.heappop(queue)
            if cell == second:
                route = [cell]
                while route[-1] in before:
                    route.append(before[route[-1]])
                return route[::-1]
            if cost > best.get(cell, cost):
                continue
            for other, step in self.steps(cell, modes):
                if other in avoid:
                    continue
                total = cost + step
                if total < best.get(other, total + 1):
                    best[other] = total
                    before[other] = cell
                    order += 1
                    heapq.heappush(queue, (total, order, other))
        return None

    def hops(self, first: Cell, second: Cell, modes: frozenset[MovementMode] | None = None) -> int | None:
        route = self.path(first, second, modes)
        if route is None:
            return None
        return sum(self.cost(a, b) for a, b in pairwise(route))

    def cost(self, first: Cell, second: Cell) -> int:
        level = (first[1] is None and second[1] is None) or passage_kind(first, second) is DeepPassageKind.LEVEL
        return 1 if level else self._vertical
