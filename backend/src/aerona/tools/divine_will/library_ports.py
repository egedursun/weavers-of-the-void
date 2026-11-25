from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, cast

from pydantic import Field, model_validator

from aerona.domain.enums.divine_will import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactStatus,
    DivineWillMode,
    ExportFormat,
    ForecastStatus,
    PlanStatus,
    StepImpact,
    StepStatus,
)
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.node import NodeKind
from aerona.engine.interconnect.flows import FlowCategory
from aerona.rules.registry import Rules
from aerona.tools.divine_will.framework import WillCall
from aerona.tools.framework.inputs import ToolInput


class LibrarySort(StrEnum):
    RELEVANCE = "relevance"
    UPDATED = "updated"
    CREATED = "created"
    TITLE = "title"
    LENGTH = "length"


class ReplaceSpec(ToolInput):
    old: str = Field(min_length=1)
    new: str


class InsertSpec(ToolInput):
    anchor: str = Field(min_length=1)
    text: str = Field(min_length=1)


class ArtifactEdit(ToolInput):
    replace: ReplaceSpec | None = None
    insert_after: InsertSpec | None = None
    append: str | None = None
    rewrite: str | None = None

    @model_validator(mode="after")
    def one_change(self) -> "ArtifactEdit":
        given = [name for name in ("replace", "insert_after", "append", "rewrite") if getattr(self, name) not in (None, "")]
        if len(given) != 1:
            raise ValueError("an edit holds exactly one of replace, insert_after, append or rewrite")
        return self


class StepDraft(ToolInput):
    title: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list)
    declared_impact: StepImpact = StepImpact.SAFE
    estimated_essence: int = Field(default=0, ge=0)


class Intervention(ToolInput):
    action_id: str = Field(min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class ArtifactDraft:
    title: str
    kind: ArtifactKind
    format: ArtifactFormat
    body: str
    language: str
    mode: DivineWillMode
    tags: Sequence[str] = ()
    node_ids: Sequence[int] = ()
    cycle_id: int | None = None
    status: ArtifactStatus = ArtifactStatus.DRAFT
    summary: str = ""


@dataclass(frozen=True)
class Ownership:
    author_account_id: int | None = None
    author_name: str | None = None
    shared: bool = False
    mine: bool = True


NO_OWNER = Ownership()


@dataclass(frozen=True)
class ArtifactPatch:
    title: str | None = None
    status: ArtifactStatus | None = None
    tags: Sequence[str] | None = None
    kind: ArtifactKind | None = None
    node_ids: Sequence[int] | None = None
    shared: bool | None = None


@dataclass(frozen=True)
class LibraryQuery:
    q: str = ""
    kind: ArtifactKind | None = None
    status: ArtifactStatus | None = None
    format: ArtifactFormat | None = None
    language: str | None = None
    mode: DivineWillMode | None = None
    tag: str | None = None
    node_id: int | None = None
    sort: LibrarySort | None = None
    offset: int = 0
    limit: int | None = None


@dataclass(frozen=True)
class Subject:
    node_id: int
    name: str
    kind: NodeKind


@dataclass(frozen=True)
class ArtifactSummary:
    id: int
    title: str
    kind: ArtifactKind
    format: ArtifactFormat
    status: ArtifactStatus
    language: str
    mode: DivineWillMode
    tags: list[str]
    subjects: list[Subject]
    current_version: int
    characters: int
    created_cycle_id: int | None
    plan_id: int | None
    created_at: datetime
    updated_at: datetime
    owner: Ownership = NO_OWNER


@dataclass(frozen=True)
class VersionSummary:
    version: int
    summary: str
    cycle_id: int | None
    characters: int
    created_at: datetime


@dataclass(frozen=True)
class VersionView:
    artifact_id: int
    version: int
    body: str
    summary: str
    cycle_id: int | None
    created_at: datetime


@dataclass(frozen=True)
class ArtifactView:
    artifact: ArtifactSummary
    body: str
    version: int
    versions: list[VersionSummary]


@dataclass(frozen=True)
class LibraryPage:
    items: list[ArtifactSummary]
    total: int
    offset: int
    limit: int
    languages: list[str]
    tags: list[str]


@dataclass(frozen=True)
class ArtifactDiff:
    artifact_id: int
    a: int
    b: int
    text: str
    added: int
    removed: int


@dataclass(frozen=True)
class ExportedFile:
    filename: str
    media_type: str
    content: bytes


@dataclass(frozen=True)
class PlanStepView:
    ordinal: int
    title: str
    action_id: str
    action_title: str
    input: dict[str, Any]
    depends_on: list[int]
    declared_impact: StepImpact
    estimated_essence: int
    status: StepStatus
    ledger_entry_id: int | None
    job_id: str
    result_text: str
    error: str


@dataclass(frozen=True)
class PlanView:
    id: int
    title: str
    status: PlanStatus
    cycle_id: int | None
    artifact_id: int | None
    approved_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    steps: list[PlanStepView]
    job_id: str = ""
    waiting_step: int | None = None
    owner: Ownership = NO_OWNER


@dataclass(frozen=True)
class TouchedNode:
    node_id: int
    name: str
    kind: NodeKind | None
    exists: bool
    status: EntityStatus | None
    stats: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class FlowDeaths:
    category: FlowCategory
    deaths: int


@dataclass(frozen=True)
class WarTally:
    ongoing: int
    begun: int
    ended: int


@dataclass(frozen=True)
class ForecastLine:
    epoch: int
    year: int | None
    text: str


@dataclass(frozen=True)
class ScenarioOutcome:
    population: int
    prosperity: float
    communities: int
    deaths: list[FlowDeaths]
    wars: WarTally
    nodes: list[TouchedNode]
    chronicle: list[ForecastLine]
    seconds: float


@dataclass(frozen=True)
class AppliedIntervention:
    action_id: str
    action_title: str
    message: str
    essence_spent: int


@dataclass(frozen=True)
class ForecastReport:
    start_epoch: int
    end_epoch: int
    start_population: int
    start_prosperity: float
    start_communities: int
    start_wars: int
    interventions: list[AppliedIntervention]
    baseline: ScenarioOutcome
    intervened: ScenarioOutcome
    seconds: float


@dataclass(frozen=True)
class ForecastEstimate:
    epochs: int
    seconds_per_epoch: float
    eta_seconds: int
    measured_epoch: int | None
    from_forecast_id: int | None


@dataclass(frozen=True)
class ForecastView:
    id: int
    cycle_id: int | None
    epochs: int
    status: ForecastStatus
    eta_seconds: int
    interventions: list[Intervention]
    report: ForecastReport | None
    job_id: str
    error: str
    epochs_done: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    owner: Ownership = NO_OWNER


class ArtifactsPort(Protocol):
    async def create(self, draft: ArtifactDraft) -> ArtifactView: ...

    async def read(self, artifact_id: int, version: int | None = None) -> ArtifactView: ...

    async def edit(self, artifact_id: int, edits: Sequence[ArtifactEdit], *, cycle_id: int | None, summary: str = "") -> ArtifactView: ...

    async def patch(self, artifact_id: int, patch: ArtifactPatch) -> ArtifactView: ...

    async def library(self, query: LibraryQuery) -> LibraryPage: ...


class PlansPort(Protocol):
    async def create(self, title: str, steps: Sequence[StepDraft], *, cycle_id: int | None) -> PlanView: ...

    async def read(self, plan_id: int) -> PlanView: ...

    async def revise(self, plan_id: int, steps: Sequence[StepDraft], *, title: str | None = None) -> PlanView: ...


class ForesightPort(Protocol):
    async def estimate(self, epochs: int, rules: Rules) -> ForecastEstimate: ...

    async def run(self, interventions: Sequence[Intervention], epochs: int, *, cycle_id: int | None, rules: Rules) -> ForecastView: ...

    async def read(self, forecast_id: int) -> ForecastView: ...


class Library(Protocol):
    @property
    def artifacts(self) -> ArtifactsPort: ...

    @property
    def plans(self) -> PlansPort: ...

    @property
    def foresight(self) -> ForesightPort: ...


class LibraryHost(Protocol):
    @property
    def library(self) -> Library: ...


def library_of(call: WillCall) -> Library:
    return cast(LibraryHost, call.services).library


EXPORT_MEDIA: dict[ExportFormat, str] = {
    ExportFormat.MD: "text/markdown; charset=utf-8",
    ExportFormat.HTML: "text/html; charset=utf-8",
    ExportFormat.PDF: "application/pdf",
    ExportFormat.EPUB: "application/epub+zip",
    ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ExportFormat.FOUNTAIN: "text/plain; charset=utf-8",
}
