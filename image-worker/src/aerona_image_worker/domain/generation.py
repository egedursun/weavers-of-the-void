from collections.abc import Callable
from dataclasses import dataclass

from aerona_image_worker.domain.enums import EventKind


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    width: int
    height: int
    steps: int
    seed: int


ProgressSink = Callable[[EventKind, int, int], None]
