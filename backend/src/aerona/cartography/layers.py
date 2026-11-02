import numpy as np
from numpy.typing import NDArray

from aerona.cartography.context import MapContext
from aerona.cartography.flood import NO_OWNER
from aerona.cartography.model import BorderKind, BorderLayer, CellLayer, KnownExtent, KnownState
from aerona.constants.cartography import COORDINATE_DECIMALS, FIELD_DECIMALS, HILLSHADE_FACTOR, HILLSHADE_MAX, HILLSHADE_MIN


def coastal_cells(context: MapContext) -> NDArray[np.bool_]:
    edges = context.mesh.edges
    crossing = context.water[edges[:, 0]] != context.water[edges[:, 1]]
    coastal = np.zeros(context.mesh.size, dtype=np.bool_)
    coastal[edges[crossing, 0]] = True
    coastal[edges[crossing, 1]] = True
    return coastal


def hillshade(context: MapContext) -> NDArray[np.float64]:
    edges = context.mesh.edges
    points = context.mesh.points
    heights = context.normalized
    first, second = edges[:, 0], edges[:, 1]
    lean = (points[second, 0] - points[first, 0] + points[second, 1] - points[first, 1]) * (heights[second] - heights[first])
    total = np.zeros(context.mesh.size, dtype=np.float64)
    np.add.at(total, first, lean)
    np.add.at(total, second, lean)
    return np.clip(total * HILLSHADE_FACTOR, HILLSHADE_MIN, HILLSHADE_MAX)


def known_cells(context: MapContext, top_owner: NDArray[np.int64], marker_cells: list[int]) -> NDArray[np.int64]:
    known = np.where(top_owner != NO_OWNER, int(KnownState.KNOWN), int(KnownState.UNKNOWN)).astype(np.int64)
    known[marker_cells] = int(KnownState.KNOWN)
    if not (known == KnownState.KNOWN).any():
        known[context.mesh.cell_at(context.mesh.window.centre)] = int(KnownState.KNOWN)
    frontier = [int(cell) for cell in np.flatnonzero(known == KnownState.KNOWN)]
    for _ in range(context.rules.cartography.fog_rings):
        following: list[int] = []
        for cell in frontier:
            for neighbour in context.mesh.neighbours[cell]:
                if known[neighbour] == KnownState.UNKNOWN:
                    known[neighbour] = int(KnownState.FOG)
                    following.append(neighbour)
        frontier = following
    return known


def known_extent(context: MapContext, known: NDArray[np.int64]) -> KnownExtent:
    settings = context.rules.cartography
    mask = known != KnownState.UNKNOWN
    points = context.mesh.points[mask]
    left, top = float(points[:, 0].min()), float(points[:, 1].min())
    right, bottom = float(points[:, 0].max()), float(points[:, 1].max())
    count = int(np.count_nonzero(mask))
    return KnownExtent(
        x=round(left, COORDINATE_DECIMALS),
        y=round(top, COORDINATE_DECIMALS),
        width=round(max(float(settings.min_extent_width), right - left), COORDINATE_DECIMALS),
        height=round(max(float(settings.min_extent_height), bottom - top), COORDINATE_DECIMALS),
        known_ratio=round(count / context.mesh.size, FIELD_DECIMALS),
        known_cells=count,
    )


def _optional_ids(values: NDArray[np.int64]) -> list[int | None]:
    return [None if value == NO_OWNER else value for value in values.tolist()]


def cell_layer(
    context: MapContext,
    *,
    biomes: NDArray[np.int64],
    coastal: NDArray[np.bool_],
    leaf_owner: NDArray[np.int64],
    top_owner: NDArray[np.int64],
    known: NDArray[np.int64],
) -> CellLayer:
    offsets: list[int] = [0]
    coordinates: list[float] = []
    for polygon in context.mesh.polygons:
        for x, y in polygon:
            coordinates.append(round(x, COORDINATE_DECIMALS))
            coordinates.append(round(y, COORDINATE_DECIMALS))
        offsets.append(len(coordinates))
    points = context.mesh.points
    return CellLayer(
        x=np.round(points[:, 0], COORDINATE_DECIMALS).tolist(),
        y=np.round(points[:, 1], COORDINATE_DECIMALS).tolist(),
        elevation=np.round(context.normalized, FIELD_DECIMALS).tolist(),
        moisture=np.round(context.moisture, FIELD_DECIMALS).tolist(),
        shade=np.round(hillshade(context), FIELD_DECIMALS).tolist(),
        water=context.water.tolist(),
        coastal=coastal.tolist(),
        biome=biomes.tolist(),
        region=_optional_ids(leaf_owner),
        top_region=_optional_ids(top_owner),
        known=known.tolist(),
        polygon_offsets=offsets,
        polygon_coordinates=coordinates,
    )


def border_layer(context: MapContext, leaf_owner: NDArray[np.int64], top_owner: NDArray[np.int64], known: NDArray[np.int64]) -> BorderLayer:
    kinds: list[BorderKind] = []
    coordinates: list[float] = []
    water = context.water
    for (first, second), segment in zip(context.mesh.edges.tolist(), context.mesh.edge_segments, strict=True):
        if segment is None or known[first] == KnownState.UNKNOWN or known[second] == KnownState.UNKNOWN:
            continue
        found: list[BorderKind] = []
        if water[first] != water[second]:
            found.append(BorderKind.COAST)
        if top_owner[first] != top_owner[second]:
            found.append(BorderKind.REGION)
        elif leaf_owner[first] != leaf_owner[second]:
            found.append(BorderKind.SUB_REGION)
        for kind in found:
            kinds.append(kind)
            coordinates.extend(round(value, COORDINATE_DECIMALS) for value in segment)
    return BorderLayer(kinds=kinds, coordinates=coordinates)
