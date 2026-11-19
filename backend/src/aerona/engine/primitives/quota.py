from collections import Counter


class WorldQuota:
    def __init__(self, cap: int) -> None:
        self.cap = cap
        self.used: Counter[int | None] = Counter()

    def full(self, world_id: int | None) -> bool:
        return self.used[world_id] >= self.cap

    def take(self, world_id: int | None) -> None:
        self.used[world_id] += 1
