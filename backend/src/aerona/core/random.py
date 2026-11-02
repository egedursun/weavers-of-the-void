import hashlib
from collections.abc import Callable, Hashable, Iterable, MutableSequence, Sequence
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")

_MASK_64 = (1 << 64) - 1
_STATE_WORDS = 4
_WORD_BYTES = 8
_FLOAT_BITS = 53
_PERCENT = 100.0
_SEPARATOR = "|"


def _rotate_left(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (64 - shift))) & _MASK_64


def derive_seed(world_seed: int, epoch: int, stream: str) -> bytes:
    material = _SEPARATOR.join((str(world_seed), str(epoch), stream)).encode("utf-8")
    return hashlib.blake2b(material, digest_size=_STATE_WORDS * _WORD_BYTES).digest()


@dataclass(frozen=True)
class RandomKey:
    world_seed: int
    epoch: int
    stream: str

    def child(self, name: str) -> "RandomKey":
        return RandomKey(self.world_seed, self.epoch, f"{self.stream}/{name}")


class SeededRandom:
    def __init__(self, key: RandomKey) -> None:
        self.key = key
        digest = derive_seed(key.world_seed, key.epoch, key.stream)
        words = [int.from_bytes(digest[index * _WORD_BYTES : (index + 1) * _WORD_BYTES], "little") for index in range(_STATE_WORDS)]
        if not any(words):
            words[0] = 1
        self._state = words
        self.draws = 0

    @classmethod
    def for_epoch(cls, world_seed: int, epoch: int, stream: str) -> "SeededRandom":
        return cls(RandomKey(world_seed, epoch, stream))

    def fork(self, name: str) -> "SeededRandom":
        return SeededRandom(self.key.child(name))

    def next_u64(self) -> int:
        s0, s1, s2, s3 = self._state
        result = (_rotate_left((s1 * 5) & _MASK_64, 7) * 9) & _MASK_64
        shifted = (s1 << 17) & _MASK_64
        s2 ^= s0
        s3 ^= s1
        s1 ^= s2
        s0 ^= s3
        s2 ^= shifted
        s3 = _rotate_left(s3, 45)
        self._state = [s0, s1, s2, s3]
        self.draws += 1
        return result

    def random(self) -> float:
        return (self.next_u64() >> (64 - _FLOAT_BITS)) / float(1 << _FLOAT_BITS)

    def below(self, bound: int) -> int:
        if bound <= 0:
            raise ValueError("bound must be positive")
        if bound == 1:
            return 0
        bits = (bound - 1).bit_length()
        while True:
            candidate = self.next_u64() >> (64 - bits)
            if candidate < bound:
                return candidate

    def integer(self, low: int, high: int) -> int:
        if high < low:
            raise ValueError("high must not be below low")
        return low + self.below(high - low + 1)

    def die(self, faces: int) -> int:
        return 1 + self.below(faces)

    def uniform(self, low: float, high: float) -> float:
        return low + (high - low) * self.random()

    def chance(self, percent: float) -> bool:
        if percent <= 0:
            return False
        if percent >= _PERCENT:
            return True
        return self.random() * _PERCENT < percent

    def probability(self, probability: float) -> bool:
        return self.chance(probability * _PERCENT)

    def pick(self, items: Sequence[T]) -> T:
        if not items:
            raise ValueError("cannot pick from an empty sequence")
        return items[self.below(len(items))]

    def pick_or_none(self, items: Sequence[T]) -> T | None:
        return self.pick(items) if items else None

    def weighted(self, items: Sequence[T], weights: Sequence[float]) -> T:
        if len(items) != len(weights) or not items:
            raise ValueError("items and weights must be non-empty and of equal length")
        if any(weight < 0 for weight in weights):
            raise ValueError("weights must not be negative")
        total = float(sum(weights))
        if total <= 0:
            return items[0]
        threshold = self.random() * total
        running = 0.0
        for item, weight in zip(items, weights, strict=True):
            running += weight
            if threshold < running:
                return item
        return next(item for item, weight in zip(reversed(items), reversed(weights), strict=True) if weight > 0)

    def weighted_by(self, items: Sequence[T], weight: Callable[[T], float]) -> T:
        return self.weighted(items, [weight(item) for item in items])

    def shuffle(self, items: MutableSequence[T]) -> None:
        for index in range(len(items) - 1, 0, -1):
            other = self.below(index + 1)
            items[index], items[other] = items[other], items[index]

    def shuffled(self, items: Iterable[T]) -> list[T]:
        result = list(items)
        self.shuffle(result)
        return result

    def sample(self, items: Sequence[T], count: int) -> list[T]:
        pool = list(items)
        size = max(0, min(count, len(pool)))
        for index in range(size):
            other = index + self.below(len(pool) - index)
            pool[index], pool[other] = pool[other], pool[index]
        return pool[:size]


def stable_order[S](items: Iterable[S], key: Callable[[S], Hashable], world_seed: int, epoch: int, stream: str) -> list[S]:
    def rank(item: S) -> bytes:
        return hashlib.blake2b(_SEPARATOR.join((str(world_seed), str(epoch), stream, repr(key(item)))).encode("utf-8"), digest_size=_WORD_BYTES).digest()

    return sorted(items, key=rank)
