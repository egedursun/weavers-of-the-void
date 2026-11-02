from pydantic import Field

from aerona.domain.enums.agent import PendingJobKind, TurnCounter
from aerona.domain.models.base import ValueObject


class PendingJob(ValueObject):
    kind: PendingJobKind
    essence: int = Field(ge=0)
    action_points: int = Field(ge=0)
    epoch: int = Field(ge=1)


class LongJobTrace(ValueObject):
    tool: str
    key: str
    summary: str


class TurnContext(ValueObject):
    counters: dict[TurnCounter, int] = Field(default_factory=dict)
    created_entity_ids: tuple[int, ...] = ()
    harvested_resource_ids: tuple[int, ...] = ()
    level_up_note: str | None = None
    pending_job: PendingJob | None = None
    long_jobs: tuple[LongJobTrace, ...] = ()

    def count(self, counter: TurnCounter) -> int:
        return self.counters.get(counter, 0)

    def bumped(self, counter: TurnCounter, amount: int = 1) -> "TurnContext":
        return self.model_copy(update={"counters": {**self.counters, counter: self.count(counter) + amount}})

    def with_creation(self, entity_id: int) -> "TurnContext":
        return self.model_copy(update={"created_entity_ids": (*self.created_entity_ids, entity_id)})

    def with_pending_job(self, job: PendingJob | None) -> "TurnContext":
        return self.model_copy(update={"pending_job": job})
