from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from aerona.db.tables.entities import EntityRow
from aerona.engine.primitives.stats import stat_or


@dataclass(frozen=True)
class RelativeThreshold:
    by_world: dict[int, float]
    ceiling: float

    def __call__(self, entity: EntityRow) -> float:
        return self.by_world.get(entity.world_id, self.ceiling)


def percentile_threshold(values: list[float], share: float, floor: float, ceiling: float) -> float:
    if not values:
        return ceiling
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * share))
    return min(ceiling, max(floor, ordered[index]))


def relative_threshold(entities: Iterable[EntityRow], key: str | Callable[[EntityRow], float], share: float, floor: float, ceiling: float) -> RelativeThreshold:
    values: dict[int, list[float]] = defaultdict(list)
    for entity in entities:
        values[entity.world_id].append(key(entity) if callable(key) else stat_or(entity, key, 0))
    return RelativeThreshold({world_id: percentile_threshold(items, share, floor, ceiling) for world_id, items in values.items()}, ceiling)
