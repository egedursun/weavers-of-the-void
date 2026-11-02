import numpy as np
import pytest

from aerona.cartography.generator import generate_map
from aerona.cartography.graph import RegionGraph
from aerona.cartography.model import BorderKind, KnownState, MapRequest, MarkerInput, RegionInput, WorldMap
from aerona.domain.enums.world import WorldType
from tests.unit.cartography.helpers import RULES, SAMPLE_REGIONS, sample_map, sample_request


def test_same_seed_gives_identical_maps() -> None:
    first = generate_map(sample_request(), RULES).world_map.model_dump_json()
    second = generate_map(sample_request(), RULES).world_map.model_dump_json()
    assert first == second
    assert generate_map(sample_request(seed="Other"), RULES).world_map.model_dump_json() != first


def test_world_map_round_trips_through_json() -> None:
    world_map = sample_map().world_map
    assert WorldMap.model_validate_json(world_map.model_dump_json()) == world_map


def test_empty_world_frames_the_centre() -> None:
    world_map = generate_map(MapRequest(seed="Aerona"), RULES).world_map
    assert (world_map.window.x, world_map.window.y, world_map.window.width, world_map.window.height) == (594, 110, 1826, 1826)
    assert len(world_map.cells.x) == 6889
    assert world_map.extent.known_cells > 0
    assert world_map.regions == []


@pytest.mark.parametrize("world_type", list(WorldType))
def test_every_world_type_generates_a_consistent_map(world_type: WorldType) -> None:
    generated = sample_map(world_type)
    world_map = generated.world_map
    cells = world_map.cells
    assert len(cells.polygon_offsets) == len(cells.x) + 1
    assert world_map.palette.world_type is world_type
    records = {record.id: record for record in world_map.regions}
    assert set(records) == {region.id for region in SAMPLE_REGIONS}
    for record in records.values():
        if record.parent_id is None:
            assert record.size > 0
    for index, region_id in enumerate(cells.region):
        if region_id is not None:
            assert cells.water[index] == records[region_id].is_water
            assert cells.top_region[index] == records[region_id].top_level_id
    edges = generated.mesh.edges
    water = np.array(cells.water)
    coastal = np.zeros(len(water), dtype=bool)
    crossing = water[edges[:, 0]] != water[edges[:, 1]]
    coastal[edges[crossing, 0]] = True
    coastal[edges[crossing, 1]] = True
    assert coastal.tolist() == cells.coastal
    for marker in world_map.markers:
        assert marker.region_id is None or marker.region_id in records


@pytest.mark.parametrize("world_type", list(WorldType))
def test_adjacency_is_symmetric_and_every_region_has_neighbours(world_type: WorldType) -> None:
    records = {record.id: record for record in sample_map(world_type).world_map.regions}
    for record in records.values():
        for other in record.neighbours:
            assert record.id in records[other].neighbours
            assert records[other].parent_id == record.parent_id
        for other in record.bordering:
            assert record.id in records[other].bordering
            assert other in record.neighbours
        siblings = [other for other in records.values() if other.parent_id == record.parent_id and other.id != record.id and other.size > 0]
        if record.size > 0 and siblings:
            assert record.neighbours


def test_distant_regions_are_still_connected_by_hops() -> None:
    request = MapRequest(
        seed="Aerona",
        regions=(RegionInput(id=1, position=(0, 0)), RegionInput(id=2, position=(3000, 0)), RegionInput(id=3, position=(6000, 2000))),
    )
    graph = generate_map(request, RULES).graph()
    assert graph.hop_distance(1, 3) is not None
    assert graph.hop_distance(1, 1) == 0
    assert graph.hop_distance(1, None) is None
    assert graph.hop_distance(1, 99) is None


def test_regions_with_the_same_position_get_distinct_seeds() -> None:
    request = MapRequest(seed="Aerona", regions=(RegionInput(id=1, position=(1500, 1000)), RegionInput(id=2, position=(1500, 1000))))
    world_map = generate_map(request, RULES).world_map
    first, second = world_map.regions
    assert first.seed != second.seed
    assert first.size > 0
    assert second.size > 0
    assert [update.id for update in world_map.relocated_positions] == [2]


def test_water_region_on_land_is_moved_to_water() -> None:
    probe = generate_map(MapRequest(seed="Aerona"), RULES)
    cells = probe.world_map.cells
    land = next(index for index, water in enumerate(cells.water) if not water)
    position = (cells.x[land], cells.y[land])
    world_map = generate_map(MapRequest(seed="Aerona", regions=(RegionInput(id=1, is_water=True, position=position),)), RULES).world_map
    record = world_map.regions[0]
    assert record.is_water
    assert [update.id for update in world_map.relocated_positions] == [1]
    assert record.elevation_class.value == "water"


def test_unpositioned_regions_receive_new_positions() -> None:
    world_map = sample_map().world_map
    updated = {update.id for update in world_map.new_positions}
    assert {region.id for region in SAMPLE_REGIONS} <= updated
    for update in world_map.new_positions:
        assert isinstance(update.x, int)


def test_third_level_regions_receive_cells() -> None:
    records = {record.id: record for record in sample_map().world_map.regions}
    assert records[7].depth == 2
    assert records[7].size > 0
    assert records[5].size >= records[7].size + records[9].size
    assert records[1].size >= records[5].size + records[6].size


def test_markers_land_inside_their_parent_region() -> None:
    generated = sample_map()
    world_map = generated.world_map
    markers = {marker.id: marker for marker in world_map.markers}
    records = {record.id: record for record in world_map.regions}
    assert set(markers) == {3, 8, 10, 11}
    assert records[markers[3].region_id or 0].top_level_id == 1
    assert records[markers[10].region_id or 0].top_level_id == 4
    assert markers[11].region_id == 2
    assert markers[3].cell != markers[8].cell
    assert len({marker.cell for marker in markers.values()}) == len(markers)


def test_marker_positions_are_kept_inside_and_relocated_outside() -> None:
    base = sample_map().world_map
    inside = next(marker for marker in base.markers if marker.id == 3)
    far = (base.window.x + 5, base.window.y + 5)
    persisted = {update.id: (float(update.x), float(update.y)) for update in base.new_positions}
    regions = tuple(region.model_copy(update={"position": persisted[region.id]}) for region in SAMPLE_REGIONS)
    request = sample_request().model_copy(
        update={"regions": regions, "markers": (MarkerInput(id=3, parent_id=1, position=(inside.x, inside.y)), MarkerInput(id=12, parent_id=4, position=far))}
    )
    world_map = generate_map(request, RULES).world_map
    markers = {marker.id: marker for marker in world_map.markers}
    assert (markers[3].x, markers[3].y) == (inside.x, inside.y)
    assert 12 in {update.id for update in world_map.relocated_positions}
    assert (markers[12].x, markers[12].y) != far


def test_known_area_and_borders() -> None:
    world_map = sample_map().world_map
    known = world_map.cells.known
    assert set(known) <= {int(state) for state in KnownState}
    assert known.count(KnownState.FOG) > 0
    assert world_map.extent.width >= RULES.cartography.min_extent_width
    kinds = set(world_map.borders.kinds)
    assert {BorderKind.COAST, BorderKind.REGION, BorderKind.SUB_REGION} <= kinds
    assert len(world_map.borders.coordinates) == 4 * len(world_map.borders.kinds)


def test_roads_follow_neighbouring_cells() -> None:
    generated = sample_map()
    world_map = generated.world_map
    start = world_map.markers[0]
    end = world_map.markers[2]
    path = generated.road((start.x, start.y), (end.x, end.y))
    assert path
    assert path[0] == (start.x, start.y)
    assert path[-1] == (end.x, end.y)


def test_region_graph_lifts_sub_regions_to_their_top_level() -> None:
    graph: RegionGraph = sample_map().graph()
    assert graph.hop_distance(7, 1) == 0
    assert graph.hop_distance(7, 4) == graph.hop_distance(1, 4)
    assert 1 in graph.within(4, 1)
    assert graph.are_neighbours(1, 4) == (graph.hop_distance(1, 4) == 1)
