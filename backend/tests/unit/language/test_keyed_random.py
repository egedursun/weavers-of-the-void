from aerona.core.keyed_random import Mulberry32, fnv1a32, keyed_random


def test_fnv1a_matches_reference_vectors() -> None:
    assert fnv1a32("") == 2166136261
    assert fnv1a32("Aerona") == 216979349
    assert fnv1a32("Aerona:h") == 1646082319
    assert fnv1a32("\u00e7a\u011f") == 3116089038


def test_mulberry32_matches_reference_sequence() -> None:
    random = Mulberry32(fnv1a32("Aerona"))
    assert [random(), random(), random()] == [0.9770483230240643, 0.40212616417557, 0.5175353118684143]


def test_keyed_random_is_reproducible() -> None:
    first = keyed_random("seed:1")
    second = keyed_random("seed:1")
    assert [first() for _ in range(5)] == [second() for _ in range(5)]
    assert 0 <= keyed_random("x").below(10) < 10
