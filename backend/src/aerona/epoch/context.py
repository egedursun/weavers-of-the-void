import time
from dataclasses import dataclass, field
from typing import Any

from aerona.agents.runtime import AgentRuntime
from aerona.core.total import partial
from aerona.db.session import Database
from aerona.domain.enums.epoch import EpochPhase, EpochStepKind, EpochStepStatus
from aerona.epoch.concurrency import StopSignal
from aerona.epoch.eta import phase_finished, phase_started
from aerona.epoch.ports import EpochHooks
from aerona.epoch.state import mark_step, raise_phase
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.rules.registry import Rules

PHASE_NAMES = partial(
    EpochPhase,
    {
        EpochPhase.GODS: "The gods' turn",
        EpochPhase.MORTALS: "The mortals' turn",
        EpochPhase.ENGINE: "The world's own course",
        EpochPhase.FATE: "Fate and the chronicler",
        EpochPhase.TRANSITION: "Epoch transition: growth, belief, essence, sky",
    },
    without={EpochPhase.NOT_STARTED},
)
PHASE_COUNT = len(PHASE_NAMES)


@dataclass
class EpochContext:
    runtime: AgentRuntime
    hooks: EpochHooks
    stop: StopSignal
    epoch: int
    resuming: bool
    job: JobContext | None = None
    started: float = field(default_factory=time.monotonic)
    engine_notes: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    sleeping_gods: set[int] = field(default_factory=set)

    @property
    def database(self) -> Database:
        return self.runtime.database

    async def rules(self) -> Rules:
        return await self.runtime.current_rules()

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def publish(self, kind: EventKind, payload: dict[str, Any]) -> None:
        self.runtime.publish(kind, {"epoch": self.epoch, **payload})

    async def enter_phase(self, phase: EpochPhase, detail: str = "") -> None:
        name = PHASE_NAMES[phase] + (f" ({detail})" if detail else "")
        async with self.database.write() as session:
            await phase_started(session, self.epoch, phase, self.elapsed())
        self.publish(EventKind.EPOCH_PROGRESS, {"no": int(phase), "total": PHASE_COUNT, "name": name, "elapsed_s": round(self.elapsed())})
        if self.job is not None:
            self.job.report((int(phase) - 1) / PHASE_COUNT, name)

    async def complete_phase(self, phase: EpochPhase) -> None:
        async with self.database.write() as session:
            await raise_phase(session, self.epoch, phase)
            await phase_finished(session, self.epoch, phase, self.elapsed())

    async def mark(self, step: EpochStepKind, status: EpochStepStatus, error: str | None = None) -> None:
        async with self.database.write() as session:
            await mark_step(session, self.epoch, step, status, error)

    def checkpoint(self, phase: int) -> None:
        self.stop.checkpoint(phase)
