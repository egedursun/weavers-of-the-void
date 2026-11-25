import base64
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

PROBE_IMAGE = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAFklEQVR42mO4ICBAEmIY1TCqYfhqAABYoPABnlzdOQAAAABJRU5ErkJggg==")
PROBE_MEDIA_TYPE = "image/png"
PROBE_SYSTEM = "Answer with one word."
PROBE_PROMPT = "Which colour fills this picture? Answer with one English word."
PROBE_ANSWER = "red"
PROBE_LABEL = "vision_probe"
PROBE_TURNS = 1
SESSION_KEY = "default"


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

    async def seen(self, message: object) -> None: ...


def content_blocks(prompt: str, images: Sequence[ImagePart]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images:
        encoded = base64.b64encode(image.data).decode("ascii")
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": image.media_type, "data": encoded}})
    return blocks


async def streamed_prompt(prompt: str, images: Sequence[ImagePart]) -> AsyncIterator[dict[str, Any]]:
    yield {
        "type": "user",
        "message": {"role": "user", "content": content_blocks(prompt, images)},
        "parent_tool_use_id": None,
        "session_id": SESSION_KEY,
    }


def probe_image() -> ImagePart:
    return ImagePart(PROBE_MEDIA_TYPE, PROBE_IMAGE)
