import hashlib
import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from aerona.constants.accounts import SECONDS_PER_DAY, SESSION_TOKEN_BYTES


def new_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SessionWindow:
    idle_days: float
    max_days: float

    def expires(self, created_at: datetime) -> datetime:
        return created_at + timedelta(seconds=self.max_days * SECONDS_PER_DAY)

    def ended(self, *, last_used_at: datetime, expires_at: datetime, now: datetime) -> bool:
        return now >= expires_at or now - last_used_at >= timedelta(seconds=self.idle_days * SECONDS_PER_DAY)


@dataclass
class AddressThrottle:
    limit: int
    window_seconds: float
    failures: dict[str, deque[float]] = field(default_factory=dict)

    def _recent(self, address: str, now: float) -> deque[float]:
        found = self.failures.setdefault(address, deque())
        while found and now - found[0] >= self.window_seconds:
            found.popleft()
        return found

    def blocked(self, address: str) -> bool:
        return len(self._recent(address, time.monotonic())) >= self.limit

    def fail(self, address: str) -> None:
        self._recent(address, time.monotonic()).append(time.monotonic())

    def clear(self, address: str) -> None:
        self.failures.pop(address, None)
