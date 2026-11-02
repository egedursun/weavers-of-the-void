import heapq
import math
from collections import defaultdict
from dataclasses import dataclass

from aerona.cartography.model import CellLayer, Coordinates, KnownState
from aerona.constants.cartography import ROAD_LAND_ELEVATION_COST, ROAD_WATER_COST, ROUTER_CACHE_SIZE

Vertex = tuple[float, float]
Edge = frozenset[Vertex]


def _polygon(cells: CellLayer, index: int) -> list[Vertex]:
    start = cells.polygon_offsets[index]
    end = cells.polygon_offsets[index + 1]
    flat = cells.polygon_coordinates[start:end]
    return [(flat[position], flat[position + 1]) for position in range(0, len(flat) - 1, 2)]


def cell_neighbours(cells: CellLayer) -> list[list[int]]:
    owners: dict[Edge, list[int]] = defaultdict(list)
    count = len(cells.polygon_offsets) - 1
    for index in range(count):
        ring = _polygon(cells, index)
        for position, vertex in enumerate(ring):
            following = ring[(position + 1) % len(ring)]
            if vertex != following:
                owners[frozenset((vertex, following))].append(index)
    neighbours: list[set[int]] = [set() for _ in range(count)]
    for shared in owners.values():
        for first in shared:
            for second in shared:
                if first != second:
                    neighbours[first].add(second)
    return [sorted(found) for found in neighbours]


@dataclass(frozen=True)
class CellGrid:
    xs: list[float]
    ys: list[float]
    left: float
    top: float
    size: float
    reach: int
    buckets: dict[tuple[int, int], list[int]]

    @classmethod
    def of(cls, cells: CellLayer) -> "CellGrid":
        xs, ys = cells.x, cells.y
        if not xs:
            return cls(xs, ys, 0.0, 0.0, 1.0, 0, {})
        left, top = min(xs), min(ys)
        span = max(max(xs) - left, max(ys) - top, 1.0)
        size = span / max(1.0, math.sqrt(len(xs)))
        buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        for index, (x, y) in enumerate(zip(xs, ys, strict=True)):
            buckets[(int((x - left) // size), int((y - top) // size))].append(index)
        return cls(xs, ys, left, top, size, math.ceil(span / size) + 1, dict(buckets))

    def _ring(self, column: int, row: int, radius: int) -> list[tuple[int, int]]:
        if radius == 0:
            return [(column, row)]
        keys = [(column + step, row - radius) for step in range(-radius, radius + 1)]
        keys += [(column + step, row + radius) for step in range(-radius, radius + 1)]
        keys += [(column - radius, row + step) for step in range(-radius + 1, radius)]
        keys += [(column + radius, row + step) for step in range(-radius + 1, radius)]
        return keys

    def nearest(self, point: Coordinates) -> int:
        column = int((point[0] - self.left) // self.size)
        row = int((point[1] - self.top) // self.size)
        best, best_distance = 0, math.inf
        for radius in range(self.reach + max(abs(column), abs(row)) + 1):
            for key in self._ring(column, row, radius):
                for index in self.buckets.get(key, ()):
                    distance = (self.xs[index] - point[0]) ** 2 + (self.ys[index] - point[1]) ** 2
                    if distance < best_distance:
                        best, best_distance = index, distance
            if best_distance <= (radius * self.size) ** 2:
                break
        return best


_TOPOLOGY: dict[int, tuple[list[list[int]], CellGrid]] = {}


def _topology(cells: CellLayer) -> tuple[list[list[int]], CellGrid]:
    key = hash((tuple(cells.x), tuple(cells.y), tuple(cells.polygon_offsets)))
    cached = _TOPOLOGY.get(key)
    if cached is None:
        cached = (cell_neighbours(cells), CellGrid.of(cells))
        _TOPOLOGY[key] = cached
        while len(_TOPOLOGY) > ROUTER_CACHE_SIZE:
            _TOPOLOGY.pop(next(iter(_TOPOLOGY)))
    return cached


@dataclass(frozen=True)
class CellRouter:
    cells: CellLayer
    neighbours: list[list[int]]
    grid: CellGrid | None = None

    @classmethod
    def of(cls, cells: CellLayer) -> "CellRouter":
        neighbours, grid = _topology(cells)
        return cls(cells, neighbours, grid)

    def cell_at(self, point: Coordinates) -> int:
        grid = self.grid or CellGrid.of(self.cells)
        return grid.nearest(point)

    def _cost(self, cell: int, neighbour: int) -> float:
        xs, ys = self.cells.x, self.cells.y
        step = math.hypot(xs[neighbour] - xs[cell], ys[neighbour] - ys[cell])
        if self.cells.water[neighbour]:
            return step * ROAD_WATER_COST
        return step * (1 + ROAD_LAND_ELEVATION_COST * max(0.0, self.cells.elevation[neighbour]))

    def route(self, start: Coordinates, end: Coordinates) -> list[float]:
        if not self.cells.x:
            return []
        origin = self.cell_at(start)
        goal = self.cell_at(end)
        best = {origin: 0.0}
        previous: dict[int, int] = {}
        heap: list[tuple[float, int]] = [(0.0, origin)]
        while heap:
            cost, cell = heapq.heappop(heap)
            if cell == goal:
                break
            if cost > best.get(cell, math.inf):
                continue
            for neighbour in self.neighbours[cell]:
                if self.cells.known[neighbour] == KnownState.UNKNOWN and neighbour != goal:
                    continue
                candidate = cost + self._cost(cell, neighbour)
                if candidate < best.get(neighbour, math.inf):
                    best[neighbour] = candidate
                    previous[neighbour] = cell
                    heapq.heappush(heap, (candidate, neighbour))
        if goal != origin and goal not in previous:
            return [start[0], start[1], end[0], end[1]]
        path = [goal]
        while path[-1] != origin:
            path.append(previous[path[-1]])
        points: list[float] = [start[0], start[1]]
        for cell in reversed(path[1:-1]):
            points += [self.cells.x[cell], self.cells.y[cell]]
        return [*points, end[0], end[1]]
