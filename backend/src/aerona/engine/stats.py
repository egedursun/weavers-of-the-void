from collections import Counter
from dataclasses import dataclass, field

from aerona.rules.registry import Rules


@dataclass
class TickStats:
    counters: Counter[str] = field(default_factory=Counter)
    phase_seconds: dict[str, float] = field(default_factory=dict)
    phase_cpu: dict[str, float] = field(default_factory=dict)
    flows: Counter[tuple[str, str, int, str]] = field(default_factory=Counter)
    grants: dict[str, int] = field(default_factory=dict)

    def count(self, key: str, amount: int = 1) -> None:
        self.counters[key] += amount

    @property
    def tick_seconds(self) -> float:
        return sum(self.phase_seconds.values())

    def over_budget(self, target_seconds: float) -> float | None:
        seconds = self.tick_seconds
        return seconds if seconds > target_seconds else None


def within_budget(rules: Rules, measured: int, budget: int) -> bool:
    return measured * 100 <= budget * (100 + rules.engine_budget.regression_pct)
