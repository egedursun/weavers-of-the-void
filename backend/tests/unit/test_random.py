from collections import Counter

import pytest

from aerona.core.random import RandomKey, SeededRandom, stable_order

DRAWS = 30000
TOLERANCE = 0.05


def draws(rng: SeededRandom, count: int) -> list[int]:
    return [rng.next_u64() for _ in range(count)]


def test_same_key_gives_the_same_sequence() -> None:
    assert draws(SeededRandom.for_epoch(42, 7, "engine"), 50) == draws(SeededRandom.for_epoch(42, 7, "engine"), 50)


def test_seed_epoch_and_stream_each_change_the_sequence() -> None:
    base = draws(SeededRandom.for_epoch(42, 7, "engine"), 10)
    assert base != draws(SeededRandom.for_epoch(43, 7, "engine"), 10)
    assert base != draws(SeededRandom.for_epoch(42, 8, "engine"), 10)
    assert base != draws(SeededRandom.for_epoch(42, 7, "war"), 10)


def test_forks_are_independent_and_deterministic() -> None:
    parent = SeededRandom.for_epoch(1, 1, "engine")
    child = parent.fork("war")
    assert child.key == RandomKey(1, 1, "engine/war")
    assert draws(child, 5) == draws(SeededRandom(RandomKey(1, 1, "engine/war")), 5)
    assert parent.draws == 0


def test_floats_and_ranges_stay_in_bounds() -> None:
    rng = SeededRandom.for_epoch(5, 1, "bounds")
    for _ in range(2000):
        assert 0.0 <= rng.random() < 1.0
        assert 3 <= rng.integer(3, 9) <= 9
        assert 1 <= rng.die(6) <= 6
    with pytest.raises(ValueError):
        rng.integer(4, 3)
    with pytest.raises(ValueError):
        rng.below(0)


def test_below_is_unbiased() -> None:
    rng = SeededRandom.for_epoch(9, 2, "uniformity")
    counts = Counter(rng.below(3) for _ in range(DRAWS))
    for value in range(3):
        assert abs(counts[value] / DRAWS - 1 / 3) < TOLERANCE


def test_chance_edges_and_rate() -> None:
    rng = SeededRandom.for_epoch(11, 3, "chance")
    assert not any(rng.chance(0) for _ in range(500))
    assert all(rng.chance(100) for _ in range(500))
    hits = sum(rng.chance(25) for _ in range(DRAWS))
    assert abs(hits / DRAWS - 0.25) < TOLERANCE


def test_weighted_choice_follows_weights() -> None:
    rng = SeededRandom.for_epoch(13, 4, "weights")
    counts = Counter(rng.weighted(["a", "b", "c"], [1, 0, 3]) for _ in range(DRAWS))
    assert counts["b"] == 0
    assert abs(counts["c"] / DRAWS - 0.75) < TOLERANCE
    assert rng.weighted(["only"], [0]) == "only"
    with pytest.raises(ValueError):
        rng.weighted(["a"], [1, 2])


def test_shuffle_is_a_deterministic_permutation() -> None:
    items = list(range(20))
    first = SeededRandom.for_epoch(17, 5, "shuffle").shuffled(items)
    second = SeededRandom.for_epoch(17, 5, "shuffle").shuffled(items)
    assert first == second
    assert sorted(first) == items
    assert first != items


def test_shuffle_positions_are_unbiased() -> None:
    rng = SeededRandom.for_epoch(19, 6, "fairness")
    firsts = Counter(rng.shuffled("abcd")[0] for _ in range(DRAWS))
    for letter in "abcd":
        assert abs(firsts[letter] / DRAWS - 0.25) < TOLERANCE


def test_sample_and_pick() -> None:
    rng = SeededRandom.for_epoch(23, 7, "sample")
    sample = rng.sample(range(10), 4)
    assert len(set(sample)) == 4
    assert rng.sample([1, 2], 5) == [2, 1] or sorted(rng.sample([1, 2], 5)) == [1, 2]
    assert rng.pick_or_none([]) is None
    with pytest.raises(ValueError):
        rng.pick([])


def test_stable_order_is_seeded() -> None:
    items = list(range(10))
    order = stable_order(items, lambda item: item, 1, 2, "words")
    assert order == stable_order(list(reversed(items)), lambda item: item, 1, 2, "words")
    assert order != stable_order(items, lambda item: item, 1, 3, "words")
