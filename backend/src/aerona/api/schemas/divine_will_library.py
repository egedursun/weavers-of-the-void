from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.domain.enums.divine_will import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactStatus,
    DivineWillMode,
    ForecastStatus,
    PlanStatus,
    StepImpact,
    StepStatus,
)
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.node import NodeKind
from aerona.engine.interconnect.flows import FlowCategory
from aerona.tools.divine_will.library_ports import LibrarySort

LIBRARY_PAGE = 24
LIBRARY_PAGE_MAX = 200


class DivineWillSubject(ApiModel):
    node_id: int
    name: str
    kind: NodeKind


class DivineWillArtifactSummary(ApiModel):
    id: int
    title: str
    kind: ArtifactKind
    format: ArtifactFormat
    status: ArtifactStatus
    language: str
    mode: DivineWillMode
    tags: list[str]
    subjects: list[DivineWillSubject]
    current_version: int
    characters: int
    created_cycle_id: int | None
    plan_id: int | None
    created_at: datetime
    updated_at: datetime


class DivineWillArtifactVersionSummary(ApiModel):
    version: int
    summary: str
    cycle_id: int | None
    characters: int
    created_at: datetime


class DivineWillArtifact(ApiModel):
    artifact: DivineWillArtifactSummary
    body: str
    version: int
    versions: list[DivineWillArtifactVersionSummary]


class DivineWillArtifactVersion(ApiModel):
    artifact_id: int
    version: int
    body: str
    summary: str
    cycle_id: int | None
    created_at: datetime


class DivineWillArtifactPage(ApiModel):
    items: list[DivineWillArtifactSummary]
    total: int
    offset: int
    limit: int
    languages: list[str]
    tags: list[str]


class DivineWillArtifactDiff(ApiModel):
    artifact_id: int
    a: int
    b: int
    text: str
    added: int
    removed: int


class DivineWillArtifactQuery(BaseModel):
    q: str = Field(default="", max_length=300)
    kind: ArtifactKind | None = None
    status: ArtifactStatus | None = None
    format: ArtifactFormat | None = None
    language: str | None = Field(default=None, max_length=60)
    mode: DivineWillMode | None = None
    tag: str | None = Field(default=None, max_length=60)
    node_id: int | None = Field(default=None, ge=1)
    sort: LibrarySort | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=LIBRARY_PAGE, ge=1, le=LIBRARY_PAGE_MAX)


class DivineWillArtifactPatch(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    status: ArtifactStatus | None = None
    tags: list[str] | None = None
    kind: ArtifactKind | None = None
    node_ids: list[int] | None = None


class DivineWillPlanStep(ApiModel):
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


class DivineWillPlan(ApiModel):
    id: int
    title: str
    status: PlanStatus
    cycle_id: int | None
    artifact_id: int | None
    approved_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    steps: list[DivineWillPlanStep]
    job_id: str
    waiting_step: int | None


class DivineWillPlanStepInput(RequestModel):
    title: str = Field(min_length=1, max_length=300)
    action_id: str = Field(min_length=1, max_length=120)
    input: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list)
    declared_impact: StepImpact = StepImpact.SAFE
    estimated_essence: int = Field(default=0, ge=0)


class DivineWillPlanSteps(RequestModel):
    steps: list[DivineWillPlanStepInput] = Field(min_length=1)
    title: str | None = Field(default=None, max_length=300)


class DivineWillIntervention(ApiModel):
    action_id: str
    input: dict[str, Any]


class DivineWillAppliedIntervention(ApiModel):
    action_id: str
    action_title: str
    message: str
    essence_spent: int


class DivineWillTouchedNode(ApiModel):
    node_id: int
    name: str
    kind: NodeKind | None
    exists: bool
    status: EntityStatus | None
    stats: dict[str, int]


class DivineWillFlowDeaths(ApiModel):
    category: FlowCategory
    deaths: int


class DivineWillWarTally(ApiModel):
    ongoing: int
    begun: int
    ended: int


class DivineWillForecastLine(ApiModel):
    epoch: int
    year: int | None
    text: str


class DivineWillScenario(ApiModel):
    population: int
    prosperity: float
    communities: int
    deaths: list[DivineWillFlowDeaths]
    wars: DivineWillWarTally
    nodes: list[DivineWillTouchedNode]
    chronicle: list[DivineWillForecastLine]
    seconds: float


class DivineWillForecastReport(ApiModel):
    start_epoch: int
    end_epoch: int
    start_population: int
    start_prosperity: float
    start_communities: int
    start_wars: int
    interventions: list[DivineWillAppliedIntervention]
    baseline: DivineWillScenario
    intervened: DivineWillScenario
    seconds: float


class DivineWillForecast(ApiModel):
    id: int
    cycle_id: int | None
    epochs: int
    status: ForecastStatus
    eta_seconds: int
    interventions: list[DivineWillIntervention]
    report: DivineWillForecastReport | None
    job_id: str
    error: str
    epochs_done: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
