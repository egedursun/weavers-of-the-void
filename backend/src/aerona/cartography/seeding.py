import math
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from aerona.cartography.context import MapContext
from aerona.cartography.model import Coordinates
from aerona.constants.cartography import REGION_SEED_SUFFIX
from aerona.core.keyed_random import keyed_random

CellList = NDArray[np.int64]


class SeedPicker:
    def __init__(self, context: MapContext) -> None:
        self._context = context
        self.used: set[int] = set()
        self.new_positions: dict[int, tuple[int, int]] = {}
        self.relocated: dict[int, tuple[int, int]] = {}

    def _usable(self, candidates: Sequence[CellList]) -> CellList:
        for cells in candidates:
            if any(int(cell) not in self.used for cell in cells):
                return cells
        return next((cells for cells in candidates if len(cells)), np.empty(0, dtype=np.int64))

    def pick(self, region_id: int, position: Coordinates | None, candidates: Sequence[CellList]) -> int | None:
        cells = self._usable(candidates)
        chosen = self._from_position(region_id, position, cells) if position is not None else self._scored(region_id, cells)
        if chosen is not None:
            self.used.add(chosen)
        return chosen

    def _from_position(self, region_id: int, position: Coordinates, cells: CellList) -> int | None:
        mesh = self._context.mesh
        wanted = np.zeros(mesh.size, dtype=np.bool_)
        wanted[cells] = True
        origin = mesh.cell_at(position)
        if wanted[origin] and origin not in self.used:
            return origin
        for cell in mesh.rings(origin, self._context.rules.cartography.seed_relocation_rings)[1:]:
            if wanted[cell] and cell not in self.used:
                self.relocated[region_id] = self._context.rounded_point(cell)
                return cell
        free = [int(cell) for cell in cells if int(cell) not in self.used]
        if free:
            distances = np.hypot(mesh.points[free, 0] - position[0], mesh.points[free, 1] - position[1])
            nearest = free[int(np.argmin(distances))]
            self.relocated[region_id] = self._context.rounded_point(nearest)
            return nearest
        if origin not in self.used:
            return origin
        return None

    def _scored(self, region_id: int, cells: CellList) -> int | None:
        context = self._context
        settings = context.rules.cartography
        free = [int(cell) for cell in cells if int(cell) not in self.used]
        if not free:
            return None
        random = keyed_random(f"{context.seed}:{REGION_SEED_SUFFIX}:{region_id}")
        used_points = context.mesh.points[sorted(self.used)] if self.used else None
        centre_x, centre_y = context.mesh.window.centre
        best = -1
        best_score = -math.inf
        for _ in range(settings.seed_attempts):
            cell = int(cells[int(random() * len(cells))])
            if cell in self.used:
                continue
            x, y = context.point(cell)
            if used_points is not None:
                nearest = float(np.min(np.hypot(used_points[:, 0] - x, used_points[:, 1] - y)))
                score = -abs(nearest - settings.seed_spacing) + random() * settings.seed_spacing_jitter
            else:
                score = -math.hypot(x - centre_x, y - centre_y) + random() * settings.first_seed_jitter
            if score > best_score:
                best = cell
                best_score = score
        chosen = best if best >= 0 else free[0]
        self.new_positions[region_id] = context.rounded_point(chosen)
        return chosen
