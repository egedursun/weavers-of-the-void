import numpy as np

from aerona.cartography.flood import NO_OWNER, FloodCosts, FloodSeed, flood, nearest_fill, water_components
from tests.unit.cartography.helpers import sample_map


def test_unbounded_flood_reaches_every_allowed_cell() -> None:
    generated = sample_map()
    mesh = generated.mesh
    everywhere = np.ones(mesh.size, dtype=np.bool_)
    costs = FloodCosts(elevation=generated.normalized, water=generated.water, elevation_cost=40.0, coast_cost=30.0)
    owner = flood(mesh, [FloodSeed(owner=1, cell=0, allowed=everywhere), FloodSeed(owner=2, cell=mesh.size - 1, allowed=everywhere)], costs, None)
    assert not (owner == NO_OWNER).any()
    assert owner[0] == 1
    assert owner[mesh.size - 1] == 2


def test_nearest_fill_labels_every_cell_and_keeps_existing_labels() -> None:
    mesh = sample_map().mesh
    labels = np.full(mesh.size, NO_OWNER, dtype=np.int64)
    labels[5] = 7
    filled = nearest_fill(mesh, labels)
    assert (filled == 7).all()


def test_water_components_measure_connected_water() -> None:
    generated = sample_map()
    sizes = water_components(generated.mesh, generated.water)
    assert (sizes[~generated.water] == 0).all()
    assert (sizes[generated.water] > 0).all()
