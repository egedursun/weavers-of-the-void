from dataclasses import dataclass
from typing import Any

from aerona.domain.enums.job import JobKind
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind

JOB_LABEL_KEY = "label"


@dataclass
class JobContext:
    job_id: str
    kind: JobKind
    params: dict[str, Any]
    bus: EventBus
    progress: float = 0.0
    stage: str | None = None

    def report(self, progress: float, stage: str | None = None) -> None:
        self.progress = max(0.0, min(1.0, progress))
        self.stage = stage
        self.bus.publish(EventKind.JOB_PROGRESS, {"job_id": self.job_id, "kind": self.kind.value, "progress": self.progress, "stage": stage})
