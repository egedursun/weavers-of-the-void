from collections.abc import Sequence
from dataclasses import dataclass, field

from aerona.cartography.model import RegionInput


@dataclass(frozen=True)
class RegionHierarchy:
    regions: dict[int, RegionInput]
    parent: dict[int, int | None]
    children: dict[int | None, list[int]] = field(default_factory=dict)

    def depth(self, region_id: int) -> int:
        return len(self.ancestors(region_id))

    def ancestors(self, region_id: int) -> list[int]:
        chain: list[int] = []
        current = self.parent[region_id]
        while current is not None:
            chain.append(current)
            current = self.parent[current]
        return chain

    def top_level(self, region_id: int) -> int:
        chain = self.ancestors(region_id)
        return chain[-1] if chain else region_id

    def member_under(self, region_id: int, group_parent: int | None) -> int | None:
        current: int | None = region_id
        while current is not None:
            if self.parent[current] == group_parent:
                return current
            current = self.parent[current]
        return None

    def breadth_first(self) -> list[int]:
        ordered: list[int] = []
        frontier = list(self.children.get(None, []))
        while frontier:
            ordered.extend(frontier)
            frontier = [child for region_id in frontier for child in self.children.get(region_id, [])]
        return ordered


def build_hierarchy(regions: Sequence[RegionInput]) -> RegionHierarchy:
    by_id = {region.id: region for region in sorted(regions, key=lambda region: region.id)}
    parent: dict[int, int | None] = {
        region_id: region.parent_id if region.parent_id in by_id and region.parent_id != region_id else None for region_id, region in by_id.items()
    }
    for region_id in by_id:
        seen = {region_id}
        current = parent[region_id]
        while current is not None:
            if current in seen:
                parent[region_id] = None
                break
            seen.add(current)
            current = parent[current]
    children: dict[int | None, list[int]] = {}
    for region_id in by_id:
        children.setdefault(parent[region_id], []).append(region_id)
    return RegionHierarchy(regions=by_id, parent=parent, children=children)
