from dataclasses import dataclass

from aerona_image_worker.domain.enums import EventKind
from aerona_image_worker.domain.generation import GenerationRequest


@dataclass(frozen=True)
class Ready:
    load_seconds: float


@dataclass(frozen=True)
class LoadFailed:
    message: str


@dataclass(frozen=True)
class Generate:
    request: GenerationRequest


@dataclass(frozen=True)
class Progress:
    kind: EventKind
    step: int
    total: int


@dataclass(frozen=True)
class Finished:
    image: bytes


@dataclass(frozen=True)
class Failed:
    message: str


@dataclass(frozen=True)
class Shutdown:
    pass


ChildMessage = Ready | LoadFailed | Progress | Finished | Failed
ParentMessage = Generate | Shutdown
