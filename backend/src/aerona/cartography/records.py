import numpy as np
from numpy.typing import NDArray

from aerona.cartography.biomes import Biome
from aerona.cartography.context import MapContext
from aerona.cartography.flood import NO_OWNER
from aerona.cartography.hierarchy import RegionHierarchy
from aerona.cartography.model import ClimateShare, Coordinates, ElevationClass, RegionRecord
from aerona.cartography.territories import Territories
from aerona.cartography.world_types import WorldTypeProfile
from aerona.constants.cartography import BIOME_COUNT, COORDINATE_DECIMALS, FIELD_DECIMALS
from aerona.constants.units import PERCENT


def region_cells(hierarchy: RegionHierarchy, leaf_owner: NDArray[np.int64]) -> dict[int, NDArray[np.int64]]:
    by_leaf: dict[int, list[int]] = {}
    for cell, leaf in enumerate(leaf_owner.tolist()):
        if leaf != NO_OWNER:
            by_leaf.setdefault(leaf, []).append(cell)
    collected: dict[int, list[int]] = {region_id: [] for region_id in hierarchy.regions}
    for leaf, cells in by_leaf.items():
        for region_id in (leaf, *hierarchy.ancestors(leaf)):
            collected[region_id].extend(cells)
    return {region_id: np.array(sorted(cells), dtype=np.int64) for region_id, cells in collected.items()}


def _rounded(point: tuple[float, float]) -> Coordinates:
    return (round(point[0], COORDINATE_DECIMALS), round(point[1], COORDINATE_DECIMALS))


def _elevation_class(is_water: bool, mean: float, context: MapContext) -> ElevationClass:
    settings = context.rules.cartography
    if is_water:
        return ElevationClass.WATER
    if mean > settings.mountainous_elevation_pct / PERCENT:
        return ElevationClass.MOUNTAINOUS
    if mean > settings.hilly_elevation_pct / PERCENT:
        return ElevationClass.HILLY
    return ElevationClass.PLAIN


def _climate(cells: NDArray[np.int64], biomes: NDArray[np.int64], profile: WorldTypeProfile, context: MapContext) -> list[ClimateShare]:
    settings = context.rules.cartography
    counts = np.bincount(biomes[cells], minlength=BIOME_COUNT)
    order = sorted(range(BIOME_COUNT), key=lambda index: -int(counts[index]))[: settings.climate_biome_count]
    shares: list[ClimateShare] = []
    for index in order:
        share = int(counts[index]) / len(cells)
        if counts[index] and share * PERCENT >= settings.climate_min_share_pct:
            shares.append(ClimateShare(biome=Biome(index), name=profile.biomes[index], share_pct=round(share * PERCENT)))
    return shares


def _anchor(cells: NDArray[np.int64], context: MapContext) -> tuple[Coordinates, Coordinates]:
    points = context.mesh.points[cells]
    centre_x = float(points[:, 0].mean())
    centre_y = float(points[:, 1].mean())
    nearest = int(cells[int(np.argmin((points[:, 0] - centre_x) ** 2 + (points[:, 1] - centre_y) ** 2))])
    return _rounded(context.point(nearest)), _rounded((centre_x, centre_y))


def build_records(
    context: MapContext,
    hierarchy: RegionHierarchy,
    *,
    territories: Territories,
    cells_by_region: dict[int, NDArray[np.int64]],
    coastal_cells: NDArray[np.bool_],
    biomes: NDArray[np.int64],
    adjacency: tuple[dict[int, set[int]], dict[int, set[int]]],
    profile: WorldTypeProfile,
) -> list[RegionRecord]:
    neighbours, bordering = adjacency
    records: dict[int, RegionRecord] = {}
    for region_id in hierarchy.breadth_first():
        region = hierarchy.regions[region_id]
        cells = cells_by_region[region_id]
        seed_cell = territories.seeds.get(region_id)
        seed = _rounded(context.point(seed_cell)) if seed_cell is not None else None
        anchor: Coordinates | None
        centroid: Coordinates | None
        parent_id = hierarchy.parent[region_id]
        if len(cells):
            anchor, centroid = _anchor(cells, context)
            mean = round(float(context.normalized[cells].mean()), FIELD_DECIMALS)
            coastal = bool(coastal_cells[cells].any())
            climate = _climate(cells, biomes, profile, context)
        else:
            parent_record = records.get(parent_id) if parent_id is not None else None
            anchor = seed or (parent_record.anchor if parent_record else None)
            centroid = anchor
            mean = 0.0
            coastal = False
            climate = []
        records[region_id] = RegionRecord(
            id=region_id,
            parent_id=parent_id,
            top_level_id=hierarchy.top_level(region_id),
            depth=hierarchy.depth(region_id),
            is_water=region.is_water,
            seed=seed,
            anchor=anchor,
            centroid=centroid,
            size=len(cells),
            coastal=coastal,
            mean_elevation=mean,
            elevation_class=_elevation_class(region.is_water, mean, context),
            climate=climate,
            neighbours=sorted(neighbours.get(region_id, set())),
            bordering=sorted(bordering.get(region_id, set())),
        )
    return [records[region_id] for region_id in sorted(records)]
