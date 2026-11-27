from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.random import SeededRandom
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.calendar import YearWindow
from aerona.engine.divine.book import DivineBook
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.recording.terms import rules_for
from aerona.engine.stats import TickStats
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules

Publisher = Callable[[EventKind, dict[str, Any]], None]


def phase_window(rules: Rules, phase: EpochPhase) -> YearWindow:
    flow = rules.epoch_flow
    windows = {
        EpochPhase.NOT_STARTED: (0, flow.year_transition),
        EpochPhase.GODS: (0, flow.year_gods),
        EpochPhase.MORTALS: (flow.year_gods, flow.year_mortals),
        EpochPhase.ENGINE: (flow.year_mortals, flow.year_engine),
        EpochPhase.FATE: (flow.year_engine, flow.year_fate),
        EpochPhase.TRANSITION: (flow.year_engine, flow.year_fate),
    }
    start, end = windows[phase]
    return YearWindow(start=min(start, end), end=max(start, end))


@dataclass
class AgingState:
    done: bool = False


@dataclass(frozen=True)
class TickEnvironment:
    rules: Rules
    epoch: int
    world_seed: int
    lore_language: LoreLanguage
    publish: Publisher
    stats: TickStats
    window: YearWindow | None = None
    progress: float | None = None
    phase: EpochPhase | None = None
    aging: AgingState | None = None
    step: float | None = None

    def rng(self, stream: str) -> SeededRandom:
        return SeededRandom.for_epoch(self.world_seed, self.epoch, stream)


@dataclass
class TickContext:
    environment: TickEnvironment
    session: AsyncSession
    phase: str
    _laws: LawBook | None = field(default=None, init=False, repr=False)
    _divine: DivineBook | None = field(default=None, init=False, repr=False)

    async def laws(self) -> LawBook:
        if self._laws is None:
            self._laws = await LawBook.load(self.session)
        return self._laws

    async def divine(self) -> DivineBook:
        if self._divine is None:
            self._divine = await DivineBook.load(self.session, self.environment.rules)
        return self._divine

    async def hook_factor(self, entity_id: int | None, hook: DomainHook) -> float:
        return await (await self.divine()).factor(self.session, entity_id, hook)

    async def hook_easing(self, entity_id: int | None, hook: DomainHook) -> float:
        return await (await self.divine()).easing(self.session, entity_id, hook)

    async def god_share(self, god_id: int, hook: DomainHook, world_id: int | None = None) -> float:
        return (await self.divine()).share(god_id, hook, world_id)

    async def hook_pct(self, entity_id: int | None, hook: DomainHook) -> float:
        return await (await self.divine()).pct(self.session, entity_id, hook)

    @property
    def rules(self) -> Rules:
        return rules_for(self.environment.rules)

    @property
    def epoch(self) -> int:
        return self.environment.epoch

    def rng(self, stream: str = "main") -> SeededRandom:
        return self.environment.rng(f"{self.phase}.{stream}")

    def count(self, key: str, amount: int = 1) -> None:
        self.environment.stats.count(f"{self.phase}.{key}", amount)

    def publish(self, kind: EventKind, payload: dict[str, Any]) -> None:
        self.environment.publish(kind, payload)
