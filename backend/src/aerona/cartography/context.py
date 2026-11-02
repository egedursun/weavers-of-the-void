from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from aerona.cartography.mesh import CellMesh
from aerona.cartography.terrain import TerrainField
from aerona.rules.registry import Rules


@dataclass
class MapContext:
    seed: str
    rules: Rules
    mesh: CellMesh
    terrain: TerrainField
    elevation: NDArray[np.float64]
    normalized: NDArray[np.float64]
    moisture: NDArray[np.float64]
    water: NDArray[np.bool_]
    wide_water: NDArray[np.bool_]

    def point(self, cell: int) -> tuple[float, float]:
        return (float(self.mesh.points[cell, 0]), float(self.mesh.points[cell, 1]))

    def rounded_point(self, cell: int) -> tuple[int, int]:
        x, y = self.point(cell)
        return (round(x), round(y))
