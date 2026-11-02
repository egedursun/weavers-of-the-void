import random

from aerona.cartography.generator import generate_map
from aerona.cartography.model import KnownState
from aerona.cartography.routing import CellGrid, CellRouter, cell_neighbours
from tests.unit.cartography.helpers import RULES, sample_request


def test_neighbours_match_the_generator_mesh() -> None:
    generated = generate_map(sample_request(), RULES)
    rebuilt = cell_neighbours(generated.world_map.cells)
    expected = [sorted(found) for found in generated.mesh.neighbours]
    matching = sum(1 for left, right in zip(rebuilt, expected, strict=True) if set(left) <= set(right))
    assert matching == len(expected)
    assert sum(len(found) for found in rebuilt) > len(rebuilt)


def test_route_runs_over_known_cells_between_its_ends() -> None:
    world_map = generate_map(sample_request(), RULES).world_map
    cells = world_map.cells
    known = [index for index, state in enumerate(cells.known) if state == KnownState.KNOWN and not cells.water[index]]
    start = (cells.x[known[0]], cells.y[known[0]])
    end = (cells.x[known[-1]], cells.y[known[-1]])
    path = CellRouter.of(cells).route(start, end)
    assert path[:2] == [start[0], start[1]]
    assert path[-2:] == [end[0], end[1]]
    assert len(path) % 2 == 0
    assert len(path) >= 4


def test_route_on_an_empty_layer_is_empty() -> None:
    world_map = generate_map(sample_request(), RULES).world_map
    empty = world_map.cells.model_copy(update={"x": [], "y": []})
    assert CellRouter(empty, []).route((0.0, 0.0), (1.0, 1.0)) == []


def test_grid_finds_the_same_nearest_cell_as_a_full_scan() -> None:
    cells = generate_map(sample_request(), RULES).world_map.cells
    grid = CellGrid.of(cells)
    rng = random.Random(7)
    left, right, top, bottom = min(cells.x), max(cells.x), min(cells.y), max(cells.y)
    for _ in range(200):
        point = (rng.uniform(left - 50, right + 50), rng.uniform(top - 50, bottom + 50))
        expected = min(range(len(cells.x)), key=lambda index: (cells.x[index] - point[0]) ** 2 + (cells.y[index] - point[1]) ** 2)
        found = grid.nearest(point)
        assert (cells.x[found] - point[0]) ** 2 + (cells.y[found] - point[1]) ** 2 == (cells.x[expected] - point[0]) ** 2 + (cells.y[expected] - point[1]) ** 2
