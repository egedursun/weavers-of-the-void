from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.random import SeededRandom
from aerona.db.repositories.chronicle import ChronicleClock, ChronicleDraft, ChronicleRepository, ChronicleWrite
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.calendar import YearWindow
from aerona.engine.primitives.knowledge import LawBook
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


@dataclass(frozen=True)
class TickEnvironment:
    rules: Rules
    epoch: int
    world_seed: int
    lore_language: LoreLanguage
    publish: Publisher
    stats: TickStats
    window: YearWindow | None = None

    def rng(self, stream: str) -> SeededRandom:
        return SeededRandom.for_epoch(self.world_seed, self.epoch, stream)


@dataclass
class TickContext:
    environment: TickEnvironment
    session: AsyncSession
    phase: str
    _laws: LawBook | None = field(default=None, init=False, repr=False)

    async def laws(self) -> LawBook:
        if self._laws is None:
            self._laws = await LawBook.load(self.session)
        return self._laws

    @property
    def rules(self) -> Rules:
        return self.environment.rules

    @property
    def epoch(self) -> int:
        return self.environment.epoch

    def rng(self, stream: str = "main") -> SeededRandom:
        return self.environment.rng(f"{self.phase}.{stream}")

    def count(self, key: str, amount: int = 1) -> None:
        self.environment.stats.count(f"{self.phase}.{key}", amount)

    def publish(self, kind: EventKind, payload: dict[str, Any]) -> None:
        self.environment.publish(kind, payload)

    async def chronicle(
        self,
        kind: ChronicleKind,
        text: str,
        *,
        template_key: str,
        entity_ids: Sequence[int] = (),
        son_id: int | None = None,
        world_id: int | None = None,
        feed_category: FeedCategory | None = None,
        window: YearWindow | None = None,
        cause_incident_id: int | None = None,
        place_entity_id: int | None = None,
        magnitude: int = 0,
        year: int | None = None,
    ) -> ChronicleWrite:
        years = self.rules.time.years_per_epoch
        clock = ChronicleClock(
            years_per_epoch=years,
            window=window or self.environment.window or YearWindow(start=0, end=years),
            pace_divisor=1,
            rng=self.rng("chronicle_year"),
        )
        draft = ChronicleDraft(
            epoch=self.epoch,
            kind=kind,
            text=text,
            entity_ids=entity_ids,
            son_id=son_id,
            world_id=world_id,
            feed_category=feed_category,
            template_key=template_key,
            cause_incident_id=cause_incident_id,
            place_entity_id=place_entity_id,
            magnitude=magnitude,
            year=year,
        )
        return await ChronicleRepository(self.session).append(draft, clock)
