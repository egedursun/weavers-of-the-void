from collections import deque
from collections.abc import Iterable

from aerona.cartography.model import RegionRecord


class RegionGraph:
    def __init__(self, records: Iterable[RegionRecord]) -> None:
        self._records = {record.id: record for record in records}
        self._top_level: dict[int, set[int]] = {}
        for record in self._records.values():
            if record.parent_id is None:
                self._top_level[record.id] = set(record.neighbours)
        for region_id, neighbours in list(self._top_level.items()):
            for other in neighbours:
                self._top_level.setdefault(other, set()).add(region_id)

    def __contains__(self, region_id: object) -> bool:
        return region_id in self._records

    def top_level_of(self, region_id: int) -> int | None:
        record = self._records.get(region_id)
        return record.top_level_id if record else None

    def neighbours(self, region_id: int) -> list[int]:
        record = self._records.get(region_id)
        return list(record.neighbours) if record else []

    def hop_distance(self, first: int | None, second: int | None) -> int | None:
        if first is None or second is None:
            return None
        start = self.top_level_of(first)
        goal = self.top_level_of(second)
        if start is None or goal is None:
            return None
        if start == goal:
            return 0
        distances = {start: 0}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbour in sorted(self._top_level.get(current, ())):
                if neighbour in distances:
                    continue
                distances[neighbour] = distances[current] + 1
                if neighbour == goal:
                    return distances[neighbour]
                queue.append(neighbour)
        return None

    def within(self, region_id: int, hops: int) -> list[int]:
        start = self.top_level_of(region_id)
        if start is None:
            return []
        distances = {start: 0}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if distances[current] >= hops:
                continue
            for neighbour in sorted(self._top_level.get(current, ())):
                if neighbour not in distances:
                    distances[neighbour] = distances[current] + 1
                    queue.append(neighbour)
        return sorted(distances)

    def are_neighbours(self, first: int | None, second: int | None) -> bool:
        distance = self.hop_distance(first, second)
        return distance is not None and distance <= 1
