from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from aerona.cartography.adjacency import sibling_adjacency
from aerona.cartography.biomes import classify_biomes
from aerona.cartography.context import MapContext
from aerona.cartography.flood import NO_OWNER, water_components
from aerona.cartography.graph import RegionGraph
from aerona.cartography.hierarchy import RegionHierarchy, build_hierarchy
from aerona.cartography.layers import border_layer, cell_layer, coastal_cells, known_cells, known_extent
from aerona.cartography.mesh import CellMesh, build_mesh, map_window
from aerona.cartography.model import Coordinates, KnownState, MapRequest, MapWindow, PlacedMarker, PositionUpdate, WorldMap
from aerona.cartography.palette import palette_for
from aerona.cartography.placement import MarkerPlacer, marker_region
from aerona.cartography.records import build_records, region_cells
from aerona.cartography.roads import trace_road
from aerona.cartography.terrain import TerrainField, terrain_settings
from aerona.cartography.territories import grow_territories
from aerona.cartography.world_types import world_type_profile
from aerona.constants.cartography import COORDINATE_DECIMALS
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class GeneratedMap:
    world_map: WorldMap
    mesh: CellMesh
    normalized: NDArray[np.float64]
    water: NDArray[np.bool_]
    known: NDArray[np.int64]

    def graph(self) -> RegionGraph:
        return RegionGraph(self.world_map.regions)

    def road(self, start: Coordinates, end: Coordinates) -> list[Coordinates]:
        return trace_road(self.mesh, elevation=self.normalized, water=self.water, passable=self.known != KnownState.UNKNOWN, start=start, end=end)


def _positions(request: MapRequest) -> list[Coordinates]:
    regions = [region.position for region in request.regions if region.position is not None]
    markers = [marker.position for marker in request.markers if marker.position is not None]
    return regions + markers


def _context(request: MapRequest, rules: Rules) -> MapContext:
    window = map_window(_positions(request), rules)
    mesh = build_mesh(request.seed, window)
    terrain = TerrainField(request.seed, terrain_settings(request.world_type, request.terrain, rules), rules)
    xs, ys = mesh.points[:, 0], mesh.points[:, 1]
    elevation = terrain.elevation(xs, ys)
    water = elevation <= terrain.sea_level
    wide_water = water & (water_components(mesh, water) >= rules.cartography.wide_water_min_cells)
    return MapContext(
        seed=request.seed,
        rules=rules,
        mesh=mesh,
        terrain=terrain,
        elevation=elevation,
        normalized=terrain.normalized(elevation),
        moisture=terrain.moisture(xs, ys),
        water=water,
        wide_water=wide_water,
    )


def _top_owner(hierarchy: RegionHierarchy, leaf_owner: NDArray[np.int64]) -> NDArray[np.int64]:
    top = leaf_owner.copy()
    for leaf in np.unique(leaf_owner).tolist():
        if leaf != NO_OWNER:
            top[leaf_owner == leaf] = hierarchy.top_level(leaf)
    return top


def _updates(positions: dict[int, tuple[int, int]]) -> list[PositionUpdate]:
    return [PositionUpdate(id=entity_id, x=x, y=y) for entity_id, (x, y) in sorted(positions.items())]


def generate_map(request: MapRequest, rules: Rules) -> GeneratedMap:
    context = _context(request, rules)
    hierarchy = build_hierarchy(request.regions)
    territories = grow_territories(context, hierarchy)
    leaf_owner = territories.leaf_owner
    top_owner = _top_owner(hierarchy, leaf_owner)
    biomes = classify_biomes(context.normalized, context.moisture, context.water, rules)
    coastal = coastal_cells(context)
    cells_by_region = region_cells(hierarchy, leaf_owner)
    profile = world_type_profile(request.world_type)
    adjacency = sibling_adjacency(context.mesh, hierarchy, leaf_owner)
    records = build_records(
        context,
        hierarchy,
        territories=territories,
        cells_by_region=cells_by_region,
        coastal_cells=coastal,
        biomes=biomes,
        adjacency=adjacency,
        profile=profile,
    )
    placement = MarkerPlacer(context, request.markers, {record.id: record for record in records}, cells_by_region, coastal).place_all()
    known = known_cells(context, top_owner, sorted(placement.cells.values()))
    markers = [
        PlacedMarker(
            id=marker_id,
            x=round(position[0], COORDINATE_DECIMALS),
            y=round(position[1], COORDINATE_DECIMALS),
            cell=placement.cells[marker_id],
            region_id=marker_region(placement.cells[marker_id], leaf_owner),
        )
        for marker_id, position in sorted(placement.positions.items())
    ]
    window = context.mesh.window
    world_map = WorldMap(
        seed=request.seed,
        world_type=request.world_type,
        window=MapWindow(x=window.left, y=window.top, width=window.width, height=window.height),
        extent=known_extent(context, known),
        palette=palette_for(request.world_type),
        cells=cell_layer(context, biomes=biomes, coastal=coastal, leaf_owner=leaf_owner, top_owner=top_owner, known=known),
        borders=border_layer(context, leaf_owner, top_owner, known),
        regions=records,
        markers=markers,
        new_positions=_updates({**territories.new_positions, **placement.new_positions}),
        relocated_positions=_updates({**territories.relocated, **placement.relocated}),
    )
    return GeneratedMap(world_map=world_map, mesh=context.mesh, normalized=context.normalized, water=context.water, known=known)
