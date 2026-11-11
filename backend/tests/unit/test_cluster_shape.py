import math

import pytest

from aerona.domain.enums.cosmography import ClusterKind
from aerona.engine.cosmos.cluster_shape import (
    CROWN_ARC_SIZE,
    FILAMENT_WAVE,
    FORGE_RING_SIZE,
    SUPERCLUSTER_HOSTS,
    scatter_of,
    slot,
    spread,
)

SPACING = 1000.0


@pytest.mark.parametrize("kind", list(ClusterKind))
def test_every_kind_places_each_galaxy_on_its_own_slot(kind: ClusterKind) -> None:
    slots = [slot(kind, index, SPACING) for index in range(40)]
    assert len(set(slots)) == len(slots)


@pytest.mark.parametrize("kind", list(ClusterKind))
def test_a_galaxy_keeps_its_slot_whatever_arrives_after_it(kind: ClusterKind) -> None:
    assert [slot(kind, index, SPACING) for index in range(10)] == [slot(kind, index, SPACING) for index in range(10)]


def test_a_filament_runs_both_ways_along_one_line() -> None:
    line = [slot(ClusterKind.FILAMENT, index, SPACING) for index in range(12)]
    bound = (FILAMENT_WAVE + scatter_of(ClusterKind.FILAMENT)) * SPACING
    assert all(abs(y) <= bound for _, y in line)
    assert min(x for x, _ in line) < -2 * SPACING < 2 * SPACING < max(x for x, _ in line)


def test_a_void_keeps_its_heart_empty() -> None:
    ring = [slot(ClusterKind.VOID, index, SPACING) for index in range(24)]
    assert min(math.hypot(x, y) for x, y in ring) > SPACING


def test_a_mirror_cluster_pairs_every_galaxy_with_its_reflection() -> None:
    for pair in range(10):
        x, y = slot(ClusterKind.MIRROR_CLUSTER, pair * 2, SPACING)
        assert x < 0
        assert slot(ClusterKind.MIRROR_CLUSTER, pair * 2 + 1, SPACING) == (-x, y)


def test_a_supercluster_gathers_its_galaxies_into_clumps() -> None:
    hosts = len(SUPERCLUSTER_HOSTS)
    clumps = [
        [slot(ClusterKind.SUPERCLUSTER, index, SPACING) for index in [clump, *(hosts + member * hosts + clump for member in range(4))]]
        for clump in range(hosts)
    ]
    centres = [(sum(x for x, _ in clump) / len(clump), sum(y for _, y in clump) / len(clump)) for clump in clumps]
    spread = max(math.hypot(x - cx, y - cy) for clump, (cx, cy) in zip(clumps, centres, strict=True) for x, y in clump)
    gap = min(math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(centres) for b in centres[i + 1 :])
    assert gap > spread


def test_a_local_group_is_held_by_two_great_galaxies() -> None:
    first, second = (slot(ClusterKind.LOCAL_GROUP, index, SPACING) for index in range(2))
    assert first[0] < 0 < second[0]


@pytest.mark.parametrize("kind", [ClusterKind.CROWN_CLUSTER, ClusterKind.FORGE_CLUSTER, ClusterKind.RICH_CLUSTER, ClusterKind.POOR_CLUSTER])
def test_a_heart_holds_the_first_galaxy(kind: ClusterKind) -> None:
    x, y = slot(kind, 0, SPACING)
    assert math.hypot(x, y) <= scatter_of(kind) * SPACING * math.sqrt(2)


def test_a_crown_sets_its_galaxies_on_one_arc_above_the_heart() -> None:
    arc = [slot(ClusterKind.CROWN_CLUSTER, index, SPACING) for index in range(1, CROWN_ARC_SIZE + 1)]
    radii = {round(math.hypot(x, y), 6) for x, y in arc}
    assert len(radii) == 1
    assert all(y < 0 for _, y in arc)


def test_a_forge_rings_its_heart_with_a_hexagon() -> None:
    ring = [slot(ClusterKind.FORGE_CLUSTER, index, SPACING) for index in range(1, FORGE_RING_SIZE + 1)]
    assert len({round(math.hypot(x, y), 6) for x, y in ring}) == 1


def test_a_dream_cluster_winds_outward() -> None:
    places = [slot(ClusterKind.DREAM_CLUSTER, index, SPACING) for index in range(16)]
    radii = [math.hypot(x, y) for x, y in places]
    assert radii[-1] > radii[0] * 2.5
    turned = sum(
        abs(math.atan2(math.sin(b - a), math.cos(b - a)))
        for a, b in zip((math.atan2(y, x) for x, y in places), (math.atan2(y, x) for x, y in places[1:]), strict=False)
    )
    assert turned > math.tau


@pytest.mark.parametrize("kind", list(ClusterKind))
def test_no_kind_sets_two_galaxies_on_top_of_each_other(kind: ClusterKind) -> None:
    places = [slot(kind, index, SPACING) for index in range(24)]
    nearest = min(math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(places) for b in places[i + 1 :])
    assert nearest > SPACING * 0.5


def test_sibling_clusters_never_crowd_each_other() -> None:
    places = [spread(index, SPACING) for index in range(30)]
    nearest = min(math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(places) for b in places[i + 1 :])
    assert nearest > SPACING


def test_the_first_cluster_of_a_dimension_sits_at_its_heart() -> None:
    assert spread(0, SPACING) == (0.0, 0.0)
