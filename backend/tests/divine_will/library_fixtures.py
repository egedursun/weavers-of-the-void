import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from aerona.db.session import Database
from aerona.db.tables.divine_will import DivineWillCycleRow, DivineWillSessionRow
from aerona.domain.enums.divine_will import ArtifactFormat, ArtifactKind, ArtifactStatus, CycleStatus, DivineWillMode
from aerona.events.bus import Event, EventBus
from aerona.events.kinds import EventKind
from aerona.services.divine_will.rule_steps import RuleSteps
from aerona.services.rule_changes import RuleDesk
from aerona.services.rules import RulesService
from aerona.tools.divine_will.library_ports import ArtifactDraft, ArtifactSummary, ArtifactView

WAIT_SECONDS = 120.0
POLL_SECONDS = 0.05


@dataclass
class Heard:
    events: list[Event] = field(default_factory=list)

    def __call__(self, event: Event) -> None:
        self.events.append(event)

    def of(self, kind: EventKind) -> list[Event]:
        return [event for event in self.events if event.kind is kind]


def rule_steps(database: Database, bus: EventBus) -> RuleSteps:
    return RuleSteps(RuleDesk(RulesService(database), database, bus, lambda: False))


def listening_bus() -> tuple[EventBus, Heard]:
    bus = EventBus()
    heard = Heard()
    bus.add_listener(heard)
    return bus, heard


async def open_cycle(database: Database, mode: DivineWillMode = DivineWillMode.CREATIVE_WORK) -> int:
    async with database.write() as session:
        opened = DivineWillSessionRow(opened_epoch=1, title="")
        session.add(opened)
        await session.flush()
        cycle = DivineWillCycleRow(session_id=opened.id, ordinal=1, mode=mode, epoch=1, status=CycleStatus.RUNNING, player_text="")
        session.add(cycle)
        await session.flush()
        return cycle.id


def draft(
    title: str = "First Draft",
    body: str = "First paragraph.\n\nSecond paragraph.",
    *,
    kind: ArtifactKind = ArtifactKind.STORY,
    form: ArtifactFormat = ArtifactFormat.MARKDOWN,
    language: str = "en",
    tags: tuple[str, ...] = (),
    node_ids: tuple[int, ...] = (),
    status: ArtifactStatus = ArtifactStatus.DRAFT,
    mode: DivineWillMode = DivineWillMode.CREATIVE_WORK,
    cycle_id: int | None = None,
) -> ArtifactDraft:
    return ArtifactDraft(title, kind, form, body, language, mode, tags, node_ids, cycle_id, status)


def view_of(body: str, form: ArtifactFormat, title: str = "Jardín Été", language: str = "es") -> ArtifactView:
    now = datetime(2026, 11, 25, tzinfo=UTC)
    summary = ArtifactSummary(
        7, title, ArtifactKind.STORY, form, ArtifactStatus.FINAL, language, DivineWillMode.CREATIVE_WORK, ["a"], [], 3, len(body), None, None, now, now
    )
    return ArtifactView(summary, body, 3, [])


async def eventually[T](read: Callable[[], Awaitable[T]], done: Callable[[T], bool], seconds: float = WAIT_SECONDS) -> T:
    waited = 0.0
    found = await read()
    while not done(found):
        if waited >= seconds:
            raise AssertionError(f"still waiting after {seconds} seconds: {found}")
        await asyncio.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
        found = await read()
    return found


@dataclass
class ScriptedPlayer:
    previews: dict[str, dict[str, Any]] = field(default_factory=dict)
    performs: dict[str, dict[str, Any]] = field(default_factory=dict)
    gate: asyncio.Event | None = None
    started: asyncio.Event = field(default_factory=asyncio.Event)
    performed: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    undone: list[int] = field(default_factory=list)

    async def preview(self, action_id: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"ok": True, "error": "", "destructive": False, "costly": False, "essence": 0, **self.previews.get(action_id, {})}

    async def perform(self, action_id: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self.performed.append((action_id, dict(payload)))
        self.started.set()
        if self.gate is not None:
            await self.gate.wait()
        return {"ok": True, "error": "", "message": f"Did {action_id}.", "ledger_entry_id": None, "job_id": "", **self.performs.get(action_id, {})}

    async def undo(self, ledger_entry_id: int) -> Mapping[str, Any]:
        self.undone.append(ledger_entry_id)
        return {"ok": True, "error": "", "entry_id": ledger_entry_id, "applied": [], "conflicts": []}

    async def job(self, job_id: str) -> Mapping[str, Any]:
        return {"ok": True, "error": "", "job_id": job_id, "status": "succeeded"}
