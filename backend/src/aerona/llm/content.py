import base64
from dataclasses import dataclass
from typing import Protocol

from aerona.llm.events import RunEvent

PROBE_IMAGE = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAFklEQVR42mO4ICBAEmIY1TCqYfhqAABYoPABnlzdOQAAAABJRU5ErkJggg==")
PROBE_MEDIA_TYPE = "image/png"


@dataclass(frozen=True)
class ImagePart:
    media_type: str
    data: bytes


@dataclass(frozen=True)
class ModelCapabilities:
    images: bool
    probed: bool
    note: str = ""


class AgentWatch(Protocol):
    @property
    def stopped(self) -> bool: ...

    async def seen(self, event: RunEvent) -> None: ...


def probe_image() -> ImagePart:
    return ImagePart(PROBE_MEDIA_TYPE, PROBE_IMAGE)
