import numpy as np
from numpy.typing import NDArray

from aerona.cartography.flood import NO_OWNER, nearest_fill
from aerona.cartography.hierarchy import RegionHierarchy
from aerona.cartography.mesh import CellMesh

Pairs = dict[int, set[int]]


def _pairs(edges: NDArray[np.int64], labels: NDArray[np.int64]) -> Pairs:
    first = labels[edges[:, 0]]
    second = labels[edges[:, 1]]
    crossing = (first != second) & (first != NO_OWNER) & (second != NO_OWNER)
    found: Pairs = {}
    for left, right in zip(first[crossing].tolist(), second[crossing].tolist(), strict=True):
        found.setdefault(left, set()).add(right)
        found.setdefault(right, set()).add(left)
    return found


def _group_labels(hierarchy: RegionHierarchy, leaf_owner: NDArray[np.int64], group_parent: int | None) -> NDArray[np.int64]:
    lookup: dict[int, int] = {}
    for leaf in np.unique(leaf_owner).tolist():
        if leaf == NO_OWNER:
            continue
        member = hierarchy.member_under(leaf, group_parent)
        if member is not None:
            lookup[leaf] = member
    table = np.vectorize(lambda leaf: lookup.get(int(leaf), NO_OWNER), otypes=[np.int64])
    return table(leaf_owner) if len(leaf_owner) else leaf_owner.copy()


def sibling_adjacency(mesh: CellMesh, hierarchy: RegionHierarchy, leaf_owner: NDArray[np.int64]) -> tuple[Pairs, Pairs]:
    neighbours: Pairs = {}
    bordering: Pairs = {}
    for group_parent, members in hierarchy.children.items():
        if len(members) < 2:
            continue
        labels = _group_labels(hierarchy, leaf_owner, group_parent)
        if np.count_nonzero(np.unique(labels) != NO_OWNER) < 2:
            continue
        for region_id, others in _pairs(mesh.edges, labels).items():
            bordering.setdefault(region_id, set()).update(others)
        for region_id, others in _pairs(mesh.edges, nearest_fill(mesh, labels)).items():
            neighbours.setdefault(region_id, set()).update(others)
    return neighbours, bordering
