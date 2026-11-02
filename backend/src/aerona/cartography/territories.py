from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from aerona.cartography.context import MapContext
from aerona.cartography.flood import NO_OWNER, FloodCosts, FloodSeed, flood
from aerona.cartography.hierarchy import RegionHierarchy
from aerona.cartography.seeding import CellList, SeedPicker


@dataclass(frozen=True)
class Territories:
    leaf_owner: NDArray[np.int64]
    seeds: dict[int, int]
    new_positions: dict[int, tuple[int, int]]
    relocated: dict[int, tuple[int, int]]


def _cells(mask: NDArray[np.bool_]) -> CellList:
    return np.flatnonzero(mask).astype(np.int64)


def _costs(context: MapContext) -> FloodCosts:
    settings = context.rules.cartography
    return FloodCosts(
        elevation=context.elevation,
        water=context.water,
        elevation_cost=float(settings.flood_elevation_cost),
        coast_cost=float(settings.flood_coast_cost),
    )


def _grow_top_level(context: MapContext, hierarchy: RegionHierarchy, picker: SeedPicker, seeds: dict[int, int]) -> NDArray[np.int64]:
    water = context.water
    every = _cells(np.ones(context.mesh.size, dtype=np.bool_))
    water_candidates = [_cells(context.wide_water), _cells(water), every]
    land_candidates = [_cells(~water), every]
    flood_seeds: list[FloodSeed] = []
    for region_id in hierarchy.children.get(None, []):
        region = hierarchy.regions[region_id]
        cell = picker.pick(region_id, region.position, water_candidates if region.is_water else land_candidates)
        if cell is None:
            continue
        seeds[region_id] = cell
        flood_seeds.append(FloodSeed(owner=region_id, cell=cell, allowed=water if region.is_water else ~water))
    return flood(context.mesh, flood_seeds, _costs(context), float(context.rules.cartography.region_radius))


def _grow_children(
    context: MapContext, hierarchy: RegionHierarchy, *, picker: SeedPicker, seeds: dict[int, int], leaf_owner: NDArray[np.int64], parent_id: int
) -> None:
    territory = leaf_owner == parent_id
    if not territory.any():
        return
    flood_seeds: list[FloodSeed] = []
    for child_id in hierarchy.children.get(parent_id, []):
        child = hierarchy.regions[child_id]
        matching = territory & (context.water == child.is_water)
        allowed = matching if matching.any() else territory
        cell = picker.pick(child_id, child.position, [_cells(matching), _cells(territory)])
        if cell is None:
            continue
        seeds[child_id] = cell
        flood_seeds.append(FloodSeed(owner=child_id, cell=cell, allowed=allowed | (np.arange(context.mesh.size) == cell)))
    if not flood_seeds:
        return
    grown = flood(context.mesh, flood_seeds, _costs(context), None)
    claimed = grown != NO_OWNER
    leaf_owner[claimed] = grown[claimed]


def _conform_terrain(context: MapContext, hierarchy: RegionHierarchy, leaf_owner: NDArray[np.int64]) -> None:
    tiny = np.finfo(np.float64).tiny
    for cell in np.flatnonzero(leaf_owner != NO_OWNER):
        wants_water = hierarchy.regions[int(leaf_owner[cell])].is_water
        if bool(context.water[cell]) == wants_water:
            continue
        context.water[cell] = wants_water
        magnitude = max(abs(float(context.normalized[cell])), tiny)
        context.normalized[cell] = -magnitude if wants_water else magnitude


def grow_territories(context: MapContext, hierarchy: RegionHierarchy) -> Territories:
    picker = SeedPicker(context)
    seeds: dict[int, int] = {}
    leaf_owner = _grow_top_level(context, hierarchy, picker, seeds)
    for region_id in hierarchy.breadth_first():
        if hierarchy.children.get(region_id):
            _grow_children(context, hierarchy, picker=picker, seeds=seeds, leaf_owner=leaf_owner, parent_id=region_id)
    _conform_terrain(context, hierarchy, leaf_owner)
    return Territories(leaf_owner=leaf_owner, seeds=seeds, new_positions=picker.new_positions, relocated=picker.relocated)
