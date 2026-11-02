from collections import Counter
from dataclasses import dataclass, field


@dataclass
class TickStats:
    counters: Counter[str] = field(default_factory=Counter)
    phase_seconds: dict[str, float] = field(default_factory=dict)
    flows: Counter[tuple[str, str, int]] = field(default_factory=Counter)

    def count(self, key: str, amount: int = 1) -> None:
        self.counters[key] += amount
