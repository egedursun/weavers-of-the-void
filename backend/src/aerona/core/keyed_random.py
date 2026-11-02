from aerona.constants.randomness import (
    FNV1A_OFFSET_BASIS,
    FNV1A_PRIME,
    MULBERRY32_FINAL_SHIFT,
    MULBERRY32_FIRST_SHIFT,
    MULBERRY32_INCREMENT,
    MULBERRY32_SECOND_MULTIPLIER_MASK,
    MULBERRY32_SECOND_SHIFT,
    UINT32_MASK,
    UINT32_RANGE,
)


def fnv1a32(text: str) -> int:
    value = FNV1A_OFFSET_BASIS
    for character in text:
        value ^= ord(character)
        value = (value * FNV1A_PRIME) & UINT32_MASK
    return value


def _imul(left: int, right: int) -> int:
    return (left * right) & UINT32_MASK


class Mulberry32:
    def __init__(self, seed: int) -> None:
        self._state = seed & UINT32_MASK

    def __call__(self) -> float:
        return self.next_float()

    def next_float(self) -> float:
        self._state = (self._state + MULBERRY32_INCREMENT) & UINT32_MASK
        state = self._state
        mixed = _imul(state ^ (state >> MULBERRY32_FIRST_SHIFT), state | 1)
        mixed = ((mixed + _imul(mixed ^ (mixed >> MULBERRY32_SECOND_SHIFT), mixed | MULBERRY32_SECOND_MULTIPLIER_MASK)) & UINT32_MASK) ^ mixed
        return ((mixed ^ (mixed >> MULBERRY32_FINAL_SHIFT)) & UINT32_MASK) / UINT32_RANGE

    def below(self, bound: int) -> int:
        return int(self.next_float() * bound)


def keyed_random(key: str) -> Mulberry32:
    return Mulberry32(fnv1a32(key))
