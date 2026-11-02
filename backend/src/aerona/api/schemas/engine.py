from aerona.api.schemas.common import ApiModel
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
