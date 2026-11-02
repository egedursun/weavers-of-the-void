import heapq
import math

import numpy as np
from numpy.typing import NDArray

from aerona.cartography.mesh import CellMesh
from aerona.cartography.model import Coordinates
from aerona.constants.cartography import COORDINATE_DECIMALS, ROAD_LAND_ELEVATION_COST, ROAD_WATER_COST


def trace_road(
    mesh: CellMesh, *, elevation: NDArray[np.float64], water: NDArray[np.bool_], passable: NDArray[np.bool_], start: Coordinates, end: Coordinates
) -> list[Coordinates]:
    origin = mesh.cell_at(start)
    goal = mesh.cell_at(end)
    best = {origin: 0.0}
    previous: dict[int, int] = {}
    heap: list[tuple[float, int]] = [(0.0, origin)]
    points = mesh.points
    while heap:
        cost, cell = heapq.heappop(heap)
        if cell == goal:
            break
        if cost > best.get(cell, math.inf):
            continue
        for neighbour in mesh.neighbours[cell]:
            if not passable[neighbour] and neighbour != goal:
                continue
            step = math.hypot(points[neighbour, 0] - points[cell, 0], points[neighbour, 1] - points[cell, 1])
            factor = ROAD_WATER_COST if water[neighbour] else 1 + ROAD_LAND_ELEVATION_COST * max(0.0, float(elevation[neighbour]))
            candidate = cost + step * factor
            if candidate < best.get(neighbour, math.inf):
                best[neighbour] = candidate
                previous[neighbour] = cell
                heapq.heappush(heap, (candidate, neighbour))
    if goal != origin and goal not in previous:
        return []
    path = [goal]
    while path[-1] != origin:
        path.append(previous[path[-1]])
    return [(round(float(points[cell, 0]), COORDINATE_DECIMALS), round(float(points[cell, 1]), COORDINATE_DECIMALS)) for cell in reversed(path)]
