from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.rules.registry import Rules

BackupHook = Callable[[str], Awaitable[str]]
SessionHook = Callable[[AsyncSession, Rules, int], Awaitable[None]]
EpochHook = Callable[[int], Awaitable[None]]
TaskHook = Callable[[], Awaitable[None]]
Spawner = Callable[[str, Callable[[], Awaitable[object]]], bool]
CountHook = Callable[[], Awaitable[int]]
Capacity = Callable[[], int]
TickHook = Callable[[int, int], Awaitable[None]]


@dataclass
class EpochHooks:
    backup: BackupHook | None = None
    complete_missing: TaskHook | None = None
    network_rule_repair: EpochHook | None = None
    prune: SessionHook | None = None
    after_epoch: EpochHook | None = None
    image_autogen: TaskHook | None = None
    spawn: Spawner | None = None
    spare: Capacity | None = None
    distribute: CountHook | None = None
    after_tick: TickHook | None = None
