from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class ActivityItem:
    node_id: int
    action: str
    other_id: int | None = None
    note: str | None = None


@dataclass
class ActivityLog:
    items: dict[tuple[int, str, int | None], ActivityItem] = field(default_factory=dict)

    def record(self, node_id: int | None, action: str, *, other_id: int | None = None, note: str | None = None) -> None:
        if node_id is None:
            return
        key = (node_id, action, other_id)
        if key not in self.items:
            self.items[key] = ActivityItem(node_id, action, other_id, note)
        elif note is not None:
            self.items[key].note = note

    def __len__(self) -> int:
        return len(self.items)


CURRENT_ACTIVITY: ContextVar[ActivityLog | None] = ContextVar("current_activity", default=None)


def current_activity() -> ActivityLog | None:
    return CURRENT_ACTIVITY.get()


@contextmanager
def collecting(log: ActivityLog) -> Iterator[ActivityLog]:
    token = CURRENT_ACTIVITY.set(log)
    try:
        yield log
    finally:
        CURRENT_ACTIVITY.reset(token)
