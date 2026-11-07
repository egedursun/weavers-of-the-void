import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import Voronoi, cKDTree

from aerona.constants.cartography import GHOST_RINGS, GRID_JITTER, WORLD_CENTRE_X, WORLD_CENTRE_Y
from aerona.core.keyed_random import keyed_random
from aerona.rules.registry import Rules

Point = tuple[float, float]
Segment = tuple[float, float, float, float]


MESH_CACHE = 8


@dataclass(frozen=True)
class GridWindow:
    left: int
    top: int
    right: int
    bottom: int
    spacing: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def centre(self) -> Point:
        return (self.left + self.width / 2, self.top + self.height / 2)


def map_window(positions: Iterable[Point], rules: Rules) -> GridWindow:
    settings = rules.cartography
    spacing = settings.grid_spacing
    pad = settings.window_padding
    known = list(positions)
    xs = [x for x, _ in known] or [WORLD_CENTRE_X]
    ys = [y for _, y in known] or [WORLD_CENTRE_Y]
    return GridWindow(
        left=math.floor((min(xs) - pad) / spacing) * spacing,
        top=math.floor((min(ys) - pad) / spacing) * spacing,
        right=math.ceil((max(xs) + pad) / spacing) * spacing,
        bottom=math.ceil((max(ys) + pad) / spacing) * spacing,
        spacing=spacing,
    )


def _jittered(seed: str, column: int, row: int, spacing: int) -> Point:
    random = keyed_random(f"{seed}:{column}:{row}")
    x = (column + 0.5 + (random() - 0.5) * GRID_JITTER) * spacing
    y = (row + 0.5 + (random() - 0.5) * GRID_JITTER) * spacing
    return (x, y)


def grid_points(seed: str, window: GridWindow) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    spacing = window.spacing
    first_column, last_column = window.left // spacing, window.right // spacing
    first_row, last_row = window.top // spacing, window.bottom // spacing
    real: list[Point] = []
    ghosts: list[Point] = []
    for row in range(first_row - GHOST_RINGS, last_row + GHOST_RINGS):
        for column in range(first_column - GHOST_RINGS, last_column + GHOST_RINGS):
            point = _jittered(seed, column, row, spacing)
            inside = first_column <= column < last_column and first_row <= row < last_row
            (real if inside else ghosts).append(point)
    return np.array(real, dtype=np.float64), np.array(ghosts, dtype=np.float64)


def _inside(point: Point, axis: int, limit: float, keep_above: bool) -> bool:
    return point[axis] >= limit if keep_above else point[axis] <= limit


def _crossing(start: Point, end: Point, axis: int, limit: float) -> Point:
    share = (limit - start[axis]) / (end[axis] - start[axis])
    other = 1 - axis
    value = start[other] + share * (end[other] - start[other])
    return (limit, value) if axis == 0 else (value, limit)


def _clip_polygon(vertices: list[Point], window: GridWindow) -> list[Point]:
    output = vertices
    for axis, limit, keep_above in ((0, window.left, True), (0, window.right, False), (1, window.top, True), (1, window.bottom, False)):
        if not output:
            break
        current = output
        output = []
        previous = current[-1]
        for point in current:
            if _inside(point, axis, limit, keep_above):
                if not _inside(previous, axis, limit, keep_above):
                    output.append(_crossing(previous, point, axis, limit))
                output.append(point)
            elif _inside(previous, axis, limit, keep_above):
                output.append(_crossing(previous, point, axis, limit))
            previous = point
    return output


def _clip_segment(segment: Segment, window: GridWindow) -> Segment | None:
    x1, y1, x2, y2 = segment
    dx, dy = x2 - x1, y2 - y1
    low, high = 0.0, 1.0
    for edge, distance in ((-dx, x1 - window.left), (dx, window.right - x1), (-dy, y1 - window.top), (dy, window.bottom - y1)):
        if edge == 0:
            if distance < 0:
                return None
            continue
        ratio = distance / edge
        if edge < 0:
            low = max(low, ratio)
        else:
            high = min(high, ratio)
        if low > high:
            return None
    return (x1 + low * dx, y1 + low * dy, x1 + high * dx, y1 + high * dy)


@dataclass(frozen=True)
class CellMesh:
    window: GridWindow
    points: NDArray[np.float64]
    neighbours: tuple[tuple[int, ...], ...]
    edges: NDArray[np.int64]
    edge_segments: tuple[Segment | None, ...]
    polygons: tuple[tuple[Point, ...], ...]
    tree: cKDTree

    @property
    def size(self) -> int:
        return len(self.points)

    def cell_at(self, point: Point) -> int:
        _, index = self.tree.query([point[0], point[1]])
        return int(index)

    def rings(self, start: int, depth: int) -> list[int]:
        seen = {start}
        frontier = [start]
        ordered = [start]
        for _ in range(depth):
            following: list[int] = []
            for cell in frontier:
                for neighbour in self.neighbours[cell]:
                    if neighbour not in seen:
                        seen.add(neighbour)
                        following.append(neighbour)
                        ordered.append(neighbour)
            frontier = following
        return ordered


def _ordered_polygon(centre: Sequence[float], vertices: NDArray[np.float64]) -> list[Point]:
    angles = np.arctan2(vertices[:, 1] - centre[1], vertices[:, 0] - centre[0])
    return [(float(vertices[index, 0]), float(vertices[index, 1])) for index in np.argsort(angles, kind="stable")]


@lru_cache(maxsize=MESH_CACHE)
def build_mesh(seed: str, window: GridWindow) -> CellMesh:
    real, ghosts = grid_points(seed, window)
    count = len(real)
    diagram = Voronoi(np.vstack([real, ghosts]))
    adjacency: list[set[int]] = [set() for _ in range(count)]
    edge_pairs: list[tuple[int, int]] = []
    segments: list[Segment | None] = []
    vertices = np.asarray(diagram.vertices, dtype=np.float64)
    for (first, second), ridge in zip(np.asarray(diagram.ridge_points).tolist(), diagram.ridge_vertices, strict=True):
        if first >= count or second >= count:
            continue
        low, high = (first, second) if first < second else (second, first)
        adjacency[low].add(high)
        adjacency[high].add(low)
        edge_pairs.append((low, high))
        if -1 in ridge or len(ridge) < 2:
            segments.append(None)
            continue
        start, end = vertices[ridge[0]], vertices[ridge[1]]
        segments.append(_clip_segment((float(start[0]), float(start[1]), float(end[0]), float(end[1])), window))
    order = sorted(range(len(edge_pairs)), key=lambda index: edge_pairs[index])
    regions = diagram.regions
    point_region = np.asarray(diagram.point_region)
    polygons: list[tuple[Point, ...]] = []
    for index in range(count):
        region = [vertex for vertex in regions[int(point_region[index])] if vertex >= 0]
        outline = _ordered_polygon(real[index], vertices[region]) if region else []
        polygons.append(tuple(_clip_polygon(outline, window)))
    return CellMesh(
        window=window,
        points=real,
        neighbours=tuple(tuple(sorted(cells)) for cells in adjacency),
        edges=np.array([edge_pairs[index] for index in order], dtype=np.int64).reshape(-1, 2),
        edge_segments=tuple(segments[index] for index in order),
        polygons=tuple(polygons),
        tree=cKDTree(real),
    )
