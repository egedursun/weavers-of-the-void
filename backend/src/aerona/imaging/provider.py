from typing import Protocol

from aerona.imaging.client import ProgressCallback
from aerona.imaging.contract import GeneratedImage, ImageJobRequest


class ImageProvider(Protocol):
    @property
    def enabled(self) -> bool: ...

    async def generate(self, job: ImageJobRequest, on_progress: ProgressCallback | None = None) -> GeneratedImage: ...

    def model_name(self) -> str: ...

    async def aclose(self) -> None: ...
