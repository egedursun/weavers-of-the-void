from pydantic import Field

from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.catalog.invariants import GenericCheck, Remedy
from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.services.engine_phases import PhaseStage
from aerona.services.integrity.manual import IntegrityTask


class EnginePhaseView(ApiModel):
    name: str
    stage: PhaseStage
    enabled: bool
    essential: bool
    heavy: bool
    runnable: bool
    rule_key: str


class EnginePhaseList(ApiModel):
    phases: list[EnginePhaseView]


class IntegrityTaskView(ApiModel):
    task: IntegrityTask
    title: str
    description: str
    changes_world: bool


class IntegrityTaskList(ApiModel):
    tasks: list[IntegrityTaskView]


class IntegrityResult(ApiModel):
    task: IntegrityTask
    counters: dict[str, int]
    message: str


class IntegrityFindingView(ApiModel):
    check: GenericCheck | None
    invariant: str | None
    table: str
    column: str | None
    key: str
    problem: str
    resolution: str
    remedy: Remedy


class IntegrityFindingList(ApiModel):
    findings: list[IntegrityFindingView]


class ResolveFinding(RequestModel):
    check: GenericCheck | None = None
    invariant: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    table: str = Field(max_length=NAME_MAX_LENGTH)
    column: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    key: str = Field(max_length=NAME_MAX_LENGTH)
