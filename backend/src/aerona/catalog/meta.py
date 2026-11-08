from dataclasses import dataclass


@dataclass(frozen=True)
class GoalSpec[K]:
    key: K
    name: str
    description: str
