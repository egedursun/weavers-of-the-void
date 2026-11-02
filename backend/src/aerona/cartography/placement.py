import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from aerona.cartography.context import MapContext
from aerona.cartography.flood import NO_OWNER
from aerona.cartography.model import Coordinates, MarkerInput, PlacementPreference, RegionRecord
from aerona.constants.cartography import POINT_SEED_SUFFIX
from aerona.constants.units import PERCENT
from aerona.core.keyed_random import Mulberry32, keyed_random


@dataclass
class Placement:
    positions: dict[int, Coordinates] = field(default_factory=dict)
    cells: dict[int, int] = field(default_factory=dict)
    new_positions: dict[int, tuple[int, int]] = field(default_factory=dict)
    relocated: dict[int, tuple[int, int]] = field(default_factory=dict)


class MarkerPlacer:
    def __init__(
        self,
        context: MapContext,
        markers: Sequence[MarkerInput],
        regions: dict[int, RegionRecord],
        cells_by_region: dict[int, NDArray[np.int64]],
        coastal_cells: NDArray[np.bool_],
    ) -> None:
        self._context = context
        self._markers = {marker.id: marker for marker in markers}
        self._regions = regions
        self._cells_by_region = cells_by_region
        self._region_sets = {region_id: set(cells.tolist()) for region_id, cells in cells_by_region.items()}
        self._coastal = coastal_cells
        self._occupied: set[int] = set()
        self.result = Placement()

    def place_all(self) -> Placement:
        for marker_id in sorted(self._markers):
            self._place(self._markers[marker_id], 0)
        return self.result

    def _inside_region(self, region_id: int, cell: int) -> bool:
        members = self._region_sets.get(region_id, set())
        return cell in members or any(neighbour in members for neighbour in self._context.mesh.neighbours[cell])

    def _place(self, marker: MarkerInput, depth: int) -> None:
        if marker.id in self.result.positions or depth > self._context.rules.cartography.point_parent_depth:
            return
        parent_id = marker.parent_id
        parent_region = self._regions.get(parent_id) if parent_id is not None else None
        parent_marker = self._markers.get(parent_id) if parent_id is not None and parent_region is None else None
        relocated = False
        if marker.position is not None:
            origin = self._context.mesh.cell_at(marker.position)
            if parent_region is None or self._inside_region(parent_region.id, origin):
                self._settle(marker.id, origin, marker.position)
                return
            relocated = True
        if parent_marker is not None and parent_marker.id not in self.result.positions:
            self._place(parent_marker, depth + 1)
        candidates = self._candidates(parent_region, parent_marker)
        if not candidates:
            return
        chosen = self._choose(marker, candidates, keyed_random(f"{self._context.seed}:{POINT_SEED_SUFFIX}:{marker.id}"))
        self._settle(marker.id, chosen, self._context.point(chosen))
        target = self.result.relocated if relocated else self.result.new_positions
        target[marker.id] = self._context.rounded_point(chosen)

    def _settle(self, marker_id: int, cell: int, position: Coordinates) -> None:
        self._occupied.add(cell)
        self.result.positions[marker_id] = position
        self.result.cells[marker_id] = cell

    def _candidates(self, parent_region: RegionRecord | None, parent_marker: MarkerInput | None) -> list[int]:
        water = self._context.water
        if parent_region is not None:
            cells = self._cells_by_region.get(parent_region.id, np.empty(0, dtype=np.int64))
            return [int(cell) for cell in cells if parent_region.is_water or not water[cell]]
        if parent_marker is not None and parent_marker.id in self.result.cells:
            rings = self._context.rules.cartography.point_parent_rings
            return [cell for cell in self._context.mesh.rings(self.result.cells[parent_marker.id], rings) if not water[cell]]
        return []

    def _choose(self, marker: MarkerInput, candidates: list[int], random: Mulberry32) -> int:
        settings = self._context.rules.cartography
        jitter = settings.point_score_jitter_pct / PERCENT
        best = -1
        best_score = -math.inf
        for _ in range(settings.point_attempts):
            cell = candidates[int(random() * len(candidates))]
            if cell in self._occupied:
                continue
            elevation = float(self._context.normalized[cell])
            if marker.preference is PlacementPreference.COASTAL_LOWLAND:
                coast = settings.settlement_coast_score_pct / PERCENT if self._coastal[cell] else 0.0
                score = coast - elevation * settings.settlement_lowland_score_pct / PERCENT + random() * jitter
            elif marker.preference is PlacementPreference.HIGHLAND:
                score = elevation * settings.resource_highland_score_pct / PERCENT + random() * jitter
            else:
                score = random()
            if score > best_score:
                best = cell
                best_score = score
        return best if best >= 0 else candidates[0]


def marker_region(cell: int, leaf_owner: NDArray[np.int64]) -> int | None:
    owner = int(leaf_owner[cell])
    return None if owner == NO_OWNER else owner
