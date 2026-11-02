import numpy as np
from numpy.typing import NDArray

from aerona.constants.cartography import (
    NOISE_DEFAULT_OCTAVES,
    NOISE_GAIN,
    NOISE_LACUNARITY,
    NOISE_LATTICE_MAX,
    NOISE_PERMUTATION_SIZE,
    NOISE_TABLE_SIZE,
)
from aerona.core.keyed_random import Mulberry32

FloatArray = NDArray[np.float64]


class ValueNoise:
    def __init__(self, seed: int) -> None:
        random = Mulberry32(seed)
        order = list(range(NOISE_PERMUTATION_SIZE))
        for index in range(NOISE_PERMUTATION_SIZE - 1, 0, -1):
            swap = int(random() * (index + 1))
            order[index], order[swap] = order[swap], order[index]
        self._table = np.array([order[index % NOISE_PERMUTATION_SIZE] for index in range(NOISE_TABLE_SIZE)], dtype=np.int64)

    def _lattice(self, column: NDArray[np.int64], row: NDArray[np.int64]) -> FloatArray:
        inner = self._table[column & (NOISE_PERMUTATION_SIZE - 1)]
        return np.asarray(self._table[(inner + row) & (NOISE_TABLE_SIZE - 1)] / NOISE_LATTICE_MAX, dtype=np.float64)

    def sample(self, x: FloatArray, y: FloatArray) -> FloatArray:
        column_floor = np.floor(x)
        row_floor = np.floor(y)
        column = column_floor.astype(np.int64)
        row = row_floor.astype(np.int64)
        fraction_x = x - column_floor
        fraction_y = y - row_floor
        top_left = self._lattice(column, row)
        top_right = self._lattice(column + 1, row)
        bottom_left = self._lattice(column, row + 1)
        bottom_right = self._lattice(column + 1, row + 1)
        smooth_x = fraction_x * fraction_x * (3 - 2 * fraction_x)
        smooth_y = fraction_y * fraction_y * (3 - 2 * fraction_y)
        return (
            top_left
            + (top_right - top_left) * smooth_x
            + (bottom_left - top_left) * smooth_y
            + (top_left - top_right - bottom_left + bottom_right) * smooth_x * smooth_y
        )

    def fractal(self, x: FloatArray, y: FloatArray, octaves: int = NOISE_DEFAULT_OCTAVES) -> FloatArray:
        total = np.zeros_like(x, dtype=np.float64)
        amplitude = 1.0
        frequency = 1.0
        norm = 0.0
        for _ in range(octaves):
            total = total + amplitude * self.sample(x * frequency, y * frequency)
            norm += amplitude
            amplitude *= NOISE_GAIN
            frequency *= NOISE_LACUNARITY
        return total / norm
