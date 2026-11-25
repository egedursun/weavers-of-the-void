import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import several
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.divine_will import (
    DivineWillArtifactNodeRow,
    DivineWillArtifactRow,
    DivineWillArtifactVersionRow,
    DivineWillAttachmentRow,
    DivineWillChunkRow,
    DivineWillConfirmationRow,
    DivineWillCycleRow,
    DivineWillEventRow,
    DivineWillForecastRow,
    DivineWillHandleRow,
    DivineWillPlanRow,
    DivineWillPlanStepRow,
    DivineWillSessionRow,
)
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.domain.enums.divine_will import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactStatus,
    AttachmentKind,
    AttachmentStatus,
    ChunkSource,
    ConfirmationReason,
    ConfirmationStatus,
    CycleEventKind,
    CycleStatus,
    DivineWillMode,
    ForecastStatus,
    PlanStatus,
    StepImpact,
    StepStatus,
)
from aerona.domain.enums.node import NodeKind
from aerona.services.books.typed import words

LEDGER_KEY = "ledger_entry_id"
NODE_KEYS = ("node_id", "target_node_id")
NODE_LIST_KEYS = ("created_ids", "node_ids")
TIME_FORMAT = "%Y-%m-%d %H:%M"
KEY_WORDS = re.compile(r"\b[a-z][a-z0-9]*(?:[_:][a-z0-9]+)+\b")

MODE_LABELS: dict[DivineWillMode, str] = {
    DivineWillMode.COMMAND: "Command",
    DivineWillMode.PLAN: "Plan",
    DivineWillMode.ASK_LORE: "Ask Lore",
    DivineWillMode.CREATIVE_WORK: "Creative Work",
    DivineWillMode.MECHANICS_GUIDE: "Mechanics Guide",
    DivineWillMode.FORESIGHT: "Foresight",
}
CYCLE_LABELS: dict[CycleStatus, str] = {
    CycleStatus.RUNNING: "Still running",
    CycleStatus.AWAITING_CONFIRMATION: "Waiting for the player's approval",
    CycleStatus.DONE: "Answered",
    CycleStatus.FAILED: "Failed",
    CycleStatus.CANCELLED: "Stopped by the player",
}
EVENT_LABELS: dict[CycleEventKind, str] = {
    CycleEventKind.PLAYER: "The player",
    CycleEventKind.THOUGHT: "Thought",
    CycleEventKind.TEXT: "Said",
    CycleEventKind.TOOL_CALL: "Tool call",
    CycleEventKind.TOOL_RESULT: "Tool result",
    CycleEventKind.CONFIRMATION_REQUEST: "Asked for approval",
    CycleEventKind.CONFIRMATION_REPLY: "The player's decision",
    CycleEventKind.NOTICE: "Notice",
    CycleEventKind.RETRY: "Retry",
    CycleEventKind.ERROR: "Error",
}
REASON_LABELS: dict[ConfirmationReason, str] = {
    ConfirmationReason.DESTRUCTIVE: "It deletes or ends something",
    ConfirmationReason.COSTLY: "It spends much essence",
    ConfirmationReason.BOTH: "It deletes or ends something and spends much essence",
}
DECISION_LABELS: dict[ConfirmationStatus, str] = {
    ConfirmationStatus.PENDING: "Waiting",
    ConfirmationStatus.APPROVED: "Approved",
    ConfirmationStatus.DECLINED: "Declined",
    ConfirmationStatus.EXPIRED: "Expired",
}
PLAN_LABELS: dict[PlanStatus, str] = {
    PlanStatus.DRAFT: "Draft",
    PlanStatus.APPROVED: "Approved",
    PlanStatus.RUNNING: "Running",
    PlanStatus.PAUSED: "Paused",
    PlanStatus.DONE: "Done",
    PlanStatus.FAILED: "Failed",
    PlanStatus.ABANDONED: "Abandoned",
}
STEP_LABELS: dict[StepStatus, str] = {
    StepStatus.PENDING: "Pending",
    StepStatus.RUNNING: "Running",
    StepStatus.DONE: "Done",
    StepStatus.SKIPPED: "Skipped",
    StepStatus.FAILED: "Failed",
    StepStatus.UNDONE: "Undone",
}
IMPACT_LABELS: dict[StepImpact, str] = {StepImpact.SAFE: "Safe", StepImpact.COSTLY: "Costly", StepImpact.DESTRUCTIVE: "Destructive"}
FORECAST_LABELS: dict[ForecastStatus, str] = {
    ForecastStatus.QUEUED: "Queued",
    ForecastStatus.RUNNING: "Running",
    ForecastStatus.DONE: "Done",
    ForecastStatus.FAILED: "Failed",
    ForecastStatus.CANCELLED: "Cancelled",
}
KIND_LABELS: dict[ArtifactKind, str] = {
    ArtifactKind.STORY: "Story",
    ArtifactKind.CHAPTER: "Chapter",
    ArtifactKind.NOVEL: "Novel",
    ArtifactKind.SCREENPLAY: "Screenplay",
    ArtifactKind.POEM: "Poem",
    ArtifactKind.CHRONICLE: "Chronicle",
    ArtifactKind.ENCYCLOPEDIA: "Encyclopedia",
    ArtifactKind.OUTLINE: "Outline",
    ArtifactKind.NOTES: "Notes",
    ArtifactKind.REPORT: "Report",
    ArtifactKind.PLAN: "Plan",
    ArtifactKind.FORECAST: "Forecast",
    ArtifactKind.HTML_PAGE: "Web page",
}
FORMAT_LABELS: dict[ArtifactFormat, str] = {ArtifactFormat.MARKDOWN: "Markdown", ArtifactFormat.FOUNTAIN: "Fountain", ArtifactFormat.HTML: "HTML"}
WRITING_LABELS: dict[ArtifactStatus, str] = {ArtifactStatus.DRAFT: "Draft", ArtifactStatus.FINAL: "Final"}
ATTACHMENT_KIND_LABELS: dict[AttachmentKind, str] = {AttachmentKind.IMAGE: "Image", AttachmentKind.DOCUMENT: "Document"}
ATTACHMENT_LABELS: dict[AttachmentStatus, str] = {
    AttachmentStatus.STORED: "Stored",
    AttachmentStatus.CONVERTED: "Converted to text",
    AttachmentStatus.INDEXED: "Converted and indexed",
    AttachmentStatus.UNREADABLE: "Unreadable",
}
SOURCE_LABELS: dict[ChunkSource, str] = {
    ChunkSource.ENTITY: "Entities",
    ChunkSource.TYPED_SECTION: "Typed sections",
    ChunkSource.CHRONICLE: "Chronicle lines",
    ChunkSource.INCIDENT: "Incidents",
    ChunkSource.SON: "Sons",
    ChunkSource.FOREIGN_GOD: "Foreign gods",
    ChunkSource.WORLD: "Worlds",
    ChunkSource.STAR: "Stars",
    ChunkSource.CREATOR: "The Creator",
    ChunkSource.WORD: "Words",
    ChunkSource.EPOCH: "Epochs",
    ChunkSource.NOTE: "Notes",
    ChunkSource.MESSAGE: "Messages",
    ChunkSource.COUNCIL: "Councils",
    ChunkSource.ARTIFACT: "Writings",
    ChunkSource.ATTACHMENT: "Attachments",
}


@dataclass(frozen=True)
class WillFact:
    label: str
    value: str


@dataclass(frozen=True)
class WillEvent:
    ordinal: int
    label: str
    tool: str
    facts: list[WillFact]
    handle: str
    handle_text: str


@dataclass(frozen=True)
class WillAct:
    entry_id: int
    tool: str
    summary: str
    epoch: int
    undone: bool
    nodes: list[tuple[str, str]]


@dataclass(frozen=True)
class WillConfirmation:
    id: int
    action_id: str
    reason: str
    decision: str
    decided: str
    input: str
    preview: list[WillFact]
    entry_id: int | None


@dataclass(frozen=True)
class WillCycle:
    ordinal: int
    mode: str
    status: str
    epoch: int
    player_text: str
    final_text: str
    facts: list[WillFact]
    error: str
    events: list[WillEvent]
    confirmations: list[WillConfirmation]
    acts: list[WillAct]


@dataclass(frozen=True)
class WillSession:
    id: int
    title: str
    open: bool
    facts: list[WillFact]
    cycles: list[WillCycle]


@dataclass(frozen=True)
class WillStep:
    ordinal: int
    title: str
    facts: list[WillFact]
    result: str
    error: str


@dataclass(frozen=True)
class WillPlan:
    id: int
    title: str
    status: str
    facts: list[WillFact]
    steps: list[WillStep]


@dataclass(frozen=True)
class WillForecast:
    id: int
    status: str
    facts: list[WillFact]
    interventions: list[WillFact]
    report: list[WillFact]


@dataclass(frozen=True)
class WillVersion:
    version: int
    summary: str
    when: str
    characters: str
    exchange: str


@dataclass(frozen=True)
class WillWriting:
    id: int
    title: str
    format: ArtifactFormat
    facts: list[WillFact]
    body: str
    versions: list[WillVersion]

    @property
    def markup(self) -> bool:
        return self.format is ArtifactFormat.HTML

    @property
    def script(self) -> bool:
        return self.format is ArtifactFormat.FOUNTAIN


@dataclass(frozen=True)
class WillAttachment:
    filename: str
    facts: list[WillFact]
    note: str


@dataclass(frozen=True)
class WillIndexLine:
    source: str
    passages: str
    tokens: str
    updated: str


@dataclass
class DivineWillRecord:
    sessions: list[WillSession] = field(default_factory=list)
    plans: list[WillPlan] = field(default_factory=list)
    forecasts: list[WillForecast] = field(default_factory=list)

    @property
    def shown(self) -> bool:
        return bool(self.sessions or self.plans or self.forecasts)

    @property
    def tally(self) -> str:
        cycles = sum(len(item.cycles) for item in self.sessions)
        return f"{several(len(self.sessions), 'session', 'sessions')}, {several(cycles, 'exchange', 'exchanges')}"


@dataclass
class DivineWillWritings:
    writings: list[WillWriting] = field(default_factory=list)
    attachments: list[WillAttachment] = field(default_factory=list)
    index: list[WillIndexLine] = field(default_factory=list)

    @property
    def shown(self) -> bool:
        return bool(self.writings or self.attachments or self.index)

    @property
    def tally(self) -> str:
        return several(len(self.writings), "writing", "writings")


ANCHORS: dict[NodeKind, str] = {
    NodeKind.ENTITY: "entity",
    NodeKind.SON: "son",
    NodeKind.CREATOR: "creator",
    NodeKind.FOREIGN_GOD: "foreign-god",
    NodeKind.WORLD: "world",
    NodeKind.STAR: "star",
    NodeKind.GALAXY: "galaxy",
    NodeKind.CLUSTER: "cluster",
    NodeKind.DIMENSION: "dimension",
}


def anchor_of(kind: NodeKind, node_id: int) -> str:
    prefix = ANCHORS[kind]
    return prefix if kind is NodeKind.CREATOR else f"{prefix}-{node_id}"


def when(moment: datetime | None) -> str:
    return moment.strftime(TIME_FORMAT) if moment is not None else ""


def text_of(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None:
        return "none"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(value, ensure_ascii=False, indent=1, default=str)


def readable(text: str) -> str:
    return KEY_WORDS.sub(lambda match: match.group(0).replace("_", " ").replace(":", " "), text)


def payload_facts(payload: Mapping[str, Any]) -> list[WillFact]:
    return [WillFact(words(str(key)), readable(text_of(value))) for key, value in payload.items() if value not in (None, "", [], {})]


def filled(*pairs: tuple[str, Any]) -> list[WillFact]:
    return [WillFact(label, readable(text_of(value))) for label, value in pairs if value not in (None, "", [], {})]


def found_values(value: Any, keys: tuple[str, ...]) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in keys:
                yield item
            yield from found_values(item, keys)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from found_values(item, keys)


def ints(values: Iterable[Any]) -> list[int]:
    found: list[int] = []
    for value in values:
        items = value if isinstance(value, list | tuple) else [value]
        found += [item for item in items if isinstance(item, int) and not isinstance(item, bool)]
    return found


def handle_text(row: DivineWillHandleRow | None) -> str:
    if row is None:
        return ""
    query = ", ".join(f"{words(str(key)).lower()} {readable(text_of(value))}" for key, value in row.query.items() if value not in (None, "", [], {}))
    return f"{several(row.total, 'item', 'items')} in all" + (f"; asked with {query}" if query else "")


@dataclass
class WillReader:
    session: AsyncSession
    names: dict[int, str]
    handles: dict[str, DivineWillHandleRow] = field(default_factory=dict)
    entries: dict[int, LedgerEntryRow] = field(default_factory=dict)

    async def load(self) -> None:
        rows = await self.session.scalars(select(DivineWillHandleRow).order_by(DivineWillHandleRow.created_at, DivineWillHandleRow.key))
        self.handles = {row.key: row for row in rows}

    async def entries_of(self, ids: Iterable[int]) -> None:
        wanted = sorted(set(ids) - set(self.entries))
        if wanted:
            self.entries.update({row.id: row for row in await self.session.scalars(select(LedgerEntryRow).where(LedgerEntryRow.id.in_(wanted)))})

    def event(self, row: DivineWillEventRow) -> WillEvent:
        return WillEvent(
            row.ordinal, EVENT_LABELS[row.kind], readable(row.tool), payload_facts(row.payload), row.handle, handle_text(self.handles.get(row.handle))
        )

    def confirmation(self, row: DivineWillConfirmationRow) -> WillConfirmation:
        decision = DECISION_LABELS[row.status]
        shown = payload_facts(row.preview)
        decided = when(row.decided_at)
        return WillConfirmation(
            row.id, readable(row.action_id), REASON_LABELS[row.reason], decision, decided, readable(text_of(row.input)), shown, row.ledger_entry_id
        )

    async def act(self, entry_id: int, nodes: Iterable[int]) -> WillAct | None:
        entry = self.entries.get(entry_id)
        if entry is None:
            return None
        touched = sorted({node for node in nodes if node in self.names})
        kinds = await NodeRepository(self.session).kinds_of(touched)
        linked = [(anchor_of(kinds[node], node), self.names[node]) for node in touched if node in kinds]
        return WillAct(entry.id, readable(entry.tool), entry.input_summary or "", entry.epoch, entry.undone, linked)

    async def cycle(self, row: DivineWillCycleRow, events: list[DivineWillEventRow], confirmations: list[DivineWillConfirmationRow]) -> WillCycle:
        payloads = [event.payload for event in events]
        entry_ids = ints(found_values(payloads, (LEDGER_KEY,))) + [item.ledger_entry_id for item in confirmations if item.ledger_entry_id is not None]
        await self.entries_of(entry_ids)
        nodes = ints(found_values(payloads, NODE_KEYS + NODE_LIST_KEYS))
        acts = [act for entry_id in sorted(set(entry_ids)) if (act := await self.act(entry_id, nodes)) is not None]
        facts = filled(
            ("Model", row.model),
            ("Tokens read", row.input_tokens),
            ("Tokens written", row.output_tokens),
            ("Model replies", row.steps),
            ("Began", when(row.started_at)),
            ("Ended", when(row.finished_at)),
        )
        return WillCycle(
            row.ordinal,
            MODE_LABELS[row.mode],
            CYCLE_LABELS[row.status],
            row.epoch,
            row.player_text,
            row.final_text,
            facts,
            row.error,
            [self.event(event) for event in events],
            [self.confirmation(item) for item in confirmations],
            acts,
        )

    async def sessions(self) -> list[WillSession]:
        events: dict[int, list[DivineWillEventRow]] = defaultdict(list)
        for event in await self.session.scalars(select(DivineWillEventRow).order_by(DivineWillEventRow.cycle_id, DivineWillEventRow.ordinal)):
            events[event.cycle_id].append(event)
        confirmations: dict[int, list[DivineWillConfirmationRow]] = defaultdict(list)
        for item in await self.session.scalars(select(DivineWillConfirmationRow).order_by(DivineWillConfirmationRow.id)):
            confirmations[item.cycle_id].append(item)
        cycles: dict[int, list[DivineWillCycleRow]] = defaultdict(list)
        for cycle in await self.session.scalars(select(DivineWillCycleRow).order_by(DivineWillCycleRow.session_id, DivineWillCycleRow.ordinal)):
            cycles[cycle.session_id].append(cycle)
        found: list[WillSession] = []
        for row in await self.session.scalars(select(DivineWillSessionRow).order_by(DivineWillSessionRow.id)):
            facts = filled(
                ("Asked by", row.author_name),
                ("Shared with the team", row.shared),
                ("Opened in epoch", row.opened_epoch),
                ("Opened", when(row.opened_at)),
                ("Closed in epoch", row.closed_epoch),
                ("Closed", when(row.closed_at)),
                ("Exchanges", len(cycles[row.id])),
            )
            shaped = [await self.cycle(cycle, events[cycle.id], confirmations[cycle.id]) for cycle in cycles[row.id]]
            found.append(WillSession(row.id, row.title, row.closed_at is None, facts, shaped))
        return found

    async def plans(self) -> list[WillPlan]:
        steps: dict[int, list[DivineWillPlanStepRow]] = defaultdict(list)
        for step in await self.session.scalars(select(DivineWillPlanStepRow).order_by(DivineWillPlanStepRow.plan_id, DivineWillPlanStepRow.ordinal)):
            steps[step.plan_id].append(step)
        titles = {row.id: row.title for row in await self.session.scalars(select(DivineWillArtifactRow).order_by(DivineWillArtifactRow.id))}
        ordinals = {row.id: row.ordinal for row in await self.session.scalars(select(DivineWillCycleRow).order_by(DivineWillCycleRow.id))}
        found: list[WillPlan] = []
        for row in await self.session.scalars(select(DivineWillPlanRow).order_by(DivineWillPlanRow.id)):
            facts = filled(
                ("Drawn by", row.author_name),
                ("Shared with the team", row.shared),
                ("Drawn in exchange", ordinals.get(row.cycle_id or 0)),
                ("Written as", titles.get(row.artifact_id or 0)),
                ("Drawn", when(row.created_at)),
                ("Approved", when(row.approved_at)),
                ("Finished", when(row.finished_at)),
            )
            shaped = [
                WillStep(
                    step.ordinal,
                    step.title,
                    filled(
                        ("Act", step.action_id),
                        ("Input", step.input),
                        ("After steps", ", ".join(str(item) for item in step.depends_on)),
                        ("Declared impact", IMPACT_LABELS[step.declared_impact]),
                        ("Essence foreseen", step.estimated_essence),
                        ("Status", STEP_LABELS[step.status]),
                        ("Ledger entry", step.ledger_entry_id),
                        ("Job", step.job_id),
                    ),
                    step.result_text,
                    step.error,
                )
                for step in steps[row.id]
            ]
            found.append(WillPlan(row.id, row.title, PLAN_LABELS[row.status], facts, shaped))
        return found

    async def forecasts(self) -> list[WillForecast]:
        ordinals = {row.id: row.ordinal for row in await self.session.scalars(select(DivineWillCycleRow).order_by(DivineWillCycleRow.id))}
        found: list[WillForecast] = []
        for row in await self.session.scalars(select(DivineWillForecastRow).order_by(DivineWillForecastRow.id)):
            facts = filled(
                ("Asked by", row.author_name),
                ("Shared with the team", row.shared),
                ("Asked in exchange", ordinals.get(row.cycle_id or 0)),
                ("Epochs foreseen", row.epochs),
                ("Expected seconds", row.eta_seconds),
                ("Job", row.job_id),
                ("Began", when(row.started_at)),
                ("Ended", when(row.finished_at)),
            )
            interventions = [WillFact(readable(str(item.get("action_id") or "act")), readable(text_of(item.get("input") or {}))) for item in row.interventions]
            found.append(WillForecast(row.id, FORECAST_LABELS[row.status], facts, interventions, payload_facts(row.report)))
        return found

    async def writings(self) -> list[WillWriting]:
        versions: dict[int, list[DivineWillArtifactVersionRow]] = defaultdict(list)
        for version in await self.session.scalars(
            select(DivineWillArtifactVersionRow).order_by(DivineWillArtifactVersionRow.artifact_id, DivineWillArtifactVersionRow.version)
        ):
            versions[version.artifact_id].append(version)
        subjects: dict[int, list[int]] = defaultdict(list)
        links = select(DivineWillArtifactNodeRow).order_by(DivineWillArtifactNodeRow.artifact_id, DivineWillArtifactNodeRow.node_id)
        for link in await self.session.scalars(links):
            subjects[link.artifact_id].append(link.node_id)
        ordinals = {row.id: row.ordinal for row in await self.session.scalars(select(DivineWillCycleRow).order_by(DivineWillCycleRow.id))}
        found: list[WillWriting] = []
        for row in await self.session.scalars(select(DivineWillArtifactRow).order_by(DivineWillArtifactRow.id)):
            kept = versions[row.id]
            current = next((item for item in kept if item.version == row.current_version), kept[-1] if kept else None)
            facts = filled(
                ("Written by", row.author_name),
                ("Shared with the team", row.shared),
                ("Kind", KIND_LABELS[row.kind]),
                ("Format", FORMAT_LABELS[row.format]),
                ("Status", WRITING_LABELS[row.status]),
                ("Language", row.language),
                ("Written in", MODE_LABELS[row.mode]),
                ("Tags", ", ".join(row.tags)),
                ("About", ", ".join(self.names.get(node, f"a lost node {node}") for node in subjects[row.id])),
                ("Begun in exchange", ordinals.get(row.created_cycle_id or 0)),
                ("Current version", row.current_version),
                ("Begun", when(row.created_at)),
                ("Last changed", when(row.updated_at)),
            )
            shaped = [
                WillVersion(
                    item.version,
                    item.summary,
                    when(item.created_at),
                    several(len(item.body), "character", "characters"),
                    str(ordinals[item.cycle_id]) if item.cycle_id in ordinals else "",
                )
                for item in kept
            ]
            found.append(WillWriting(row.id, row.title, row.format, facts, current.body if current is not None else "", shaped))
        return found

    async def attachments(self) -> list[WillAttachment]:
        ordinals = {row.id: row.ordinal for row in await self.session.scalars(select(DivineWillCycleRow).order_by(DivineWillCycleRow.id))}
        return [
            WillAttachment(
                row.filename,
                filled(
                    ("Kind", ATTACHMENT_KIND_LABELS[row.kind]),
                    ("File type", row.mime),
                    ("Size", several(row.size, "byte", "bytes")),
                    ("State", ATTACHMENT_LABELS[row.status]),
                    ("Seen by the model", row.seen_by_model),
                    ("Brought in exchange", ordinals.get(row.cycle_id or 0)),
                    ("Brought", when(row.created_at)),
                ),
                row.note,
            )
            for row in await self.session.scalars(select(DivineWillAttachmentRow).order_by(DivineWillAttachmentRow.id))
        ]

    async def index(self) -> list[WillIndexLine]:
        counted = await self.session.execute(
            select(DivineWillChunkRow.source, func.count(), func.sum(DivineWillChunkRow.tokens), func.max(DivineWillChunkRow.updated_epoch))
            .group_by(DivineWillChunkRow.source)
            .order_by(DivineWillChunkRow.source)
        )
        return [
            WillIndexLine(
                SOURCE_LABELS[source], several(int(passages), "passage", "passages"), several(int(tokens or 0), "token", "tokens"), f"epoch {latest or 0}"
            )
            for source, passages, tokens, latest in counted
        ]


async def divine_will_record(session: AsyncSession, names: dict[int, str]) -> DivineWillRecord:
    reader = WillReader(session, names)
    await reader.load()
    return DivineWillRecord(await reader.sessions(), await reader.plans(), await reader.forecasts())


async def divine_will_writings(session: AsyncSession, names: dict[int, str]) -> DivineWillWritings:
    reader = WillReader(session, names)
    return DivineWillWritings(await reader.writings(), await reader.attachments(), await reader.index())
