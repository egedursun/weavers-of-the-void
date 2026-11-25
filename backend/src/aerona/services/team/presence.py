import time
from dataclasses import dataclass, field

from aerona.core.account_scope import AccountRef


@dataclass(frozen=True)
class Presence:
    account_id: int
    name: str
    screen: str
    node_id: int | None
    editing: bool
    seen: float


@dataclass
class Roster:
    present: dict[int, Presence] = field(default_factory=dict)

    def mark(self, account: AccountRef, screen: str, node_id: int | None, editing: bool, now: float | None = None) -> Presence:
        found = Presence(account.id, account.name, screen, node_id, editing, time.monotonic() if now is None else now)
        self.present[account.id] = found
        return found

    def leave(self, account_id: int) -> bool:
        return self.present.pop(account_id, None) is not None

    def live(self, ttl: float, now: float | None = None) -> list[Presence]:
        moment = time.monotonic() if now is None else now
        for account_id in [key for key, seen in self.present.items() if moment - seen.seen > ttl]:
            del self.present[account_id]
        return sorted(self.present.values(), key=lambda item: (item.name.casefold(), item.account_id))
