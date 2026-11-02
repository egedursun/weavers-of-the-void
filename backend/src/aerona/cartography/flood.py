import heapq
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from aerona.cartography.mesh import CellMesh

NO_OWNER = -1


@dataclass(frozen=True)
class FloodSeed:
    owner: int
    cell: int
    allowed: NDArray[np.bool_]


@dataclass(frozen=True)
class FloodCosts:
    elevation: NDArray[np.float64]
    water: NDArray[np.bool_]
    elevation_cost: float
    coast_cost: float


def flood(mesh: CellMesh, seeds: Sequence[FloodSeed], costs: FloodCosts, radius: float | None) -> NDArray[np.int64]:
    owner = np.full(mesh.size, NO_OWNER, dtype=np.int64)
    best = np.full(mesh.size, math.inf, dtype=np.float64)
    allowed: dict[int, NDArray[np.bool_]] = {}
    centres: dict[int, tuple[float, float]] = {}
    heap: list[tuple[float, int, int]] = []
    for seed in seeds:
        best[seed.cell] = 0.0
        owner[seed.cell] = seed.owner
        allowed[seed.owner] = seed.allowed
        centres[seed.owner] = (float(mesh.points[seed.cell, 0]), float(mesh.points[seed.cell, 1]))
        heapq.heappush(heap, (0.0, seed.cell, seed.owner))
    points = mesh.points
    elevation = costs.elevation
    water = costs.water
    while heap:
        cost, cell, region = heapq.heappop(heap)
        if cost > best[cell]:
            continue
        mask = allowed[region]
        centre_x, centre_y = centres[region]
        for neighbour in mesh.neighbours[cell]:
            if not mask[neighbour]:
                continue
            if radius is not None and math.hypot(points[neighbour, 0] - centre_x, points[neighbour, 1] - centre_y) > radius:
                continue
            step = 1.0 + abs(elevation[neighbour] - elevation[cell]) * costs.elevation_cost
            if water[neighbour] != water[cell]:
                step += costs.coast_cost
            candidate = cost + step
            if candidate < best[neighbour]:
                best[neighbour] = candidate
                owner[neighbour] = region
                heapq.heappush(heap, (candidate, neighbour, region))
    return owner


def nearest_fill(mesh: CellMesh, labels: NDArray[np.int64]) -> NDArray[np.int64]:
    filled = labels.copy()
    queue = [int(cell) for cell in np.flatnonzero(filled != NO_OWNER)]
    position = 0
    while position < len(queue):
        cell = queue[position]
        position += 1
        for neighbour in mesh.neighbours[cell]:
            if filled[neighbour] == NO_OWNER:
                filled[neighbour] = filled[cell]
                queue.append(neighbour)
    return filled


def water_components(mesh: CellMesh, water: NDArray[np.bool_]) -> NDArray[np.int64]:
    sizes = np.zeros(mesh.size, dtype=np.int64)
    visited = np.zeros(mesh.size, dtype=np.bool_)
    for start in range(mesh.size):
        if not water[start] or visited[start]:
            continue
        visited[start] = True
        component = [start]
        position = 0
        while position < len(component):
            cell = component[position]
            position += 1
            for neighbour in mesh.neighbours[cell]:
                if water[neighbour] and not visited[neighbour]:
                    visited[neighbour] = True
                    component.append(neighbour)
        sizes[component] = len(component)
    return sizes
