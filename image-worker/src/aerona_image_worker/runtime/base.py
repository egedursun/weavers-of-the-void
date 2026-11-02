from typing import Protocol

from aerona_image_worker.domain.generation import GenerationRequest, ProgressSink


class Runner(Protocol):
    @property
    def loaded(self) -> bool: ...

    async def ensure_loaded(self, limit_seconds: float) -> None: ...

    async def generate(self, request: GenerationRequest, limit_seconds: float, report: ProgressSink) -> bytes: ...

    async def unload(self) -> None: ...
