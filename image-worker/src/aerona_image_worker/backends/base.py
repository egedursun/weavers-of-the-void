from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from aerona_image_worker.domain.enums import BackendName
from aerona_image_worker.domain.generation import GenerationRequest, ProgressSink


@dataclass(frozen=True)
class BackendSpec:
    name: BackendName
    model_id: str
    fake_load_seconds: float = 0.0
    fake_step_seconds: float = 0.0
    fake_failure_prompt: str = ""


class ImageBackend(Protocol):
    def load(self) -> None: ...

    def generate(self, request: GenerationRequest, report: ProgressSink) -> bytes: ...

    def unload(self) -> None: ...


BackendFactory = Callable[[BackendSpec], ImageBackend]
