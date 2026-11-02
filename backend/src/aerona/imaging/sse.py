from collections.abc import AsyncIterator
from dataclasses import dataclass, field

FIELD_SEPARATOR = ":"
COMMENT_PREFIX = ":"


@dataclass(frozen=True)
class SseMessage:
    data: str
    event: str | None = None
    event_id: str | None = None


@dataclass
class SseBuffer:
    data: list[str] = field(default_factory=list)
    event: str | None = None
    event_id: str | None = None

    def feed(self, line: str) -> SseMessage | None:
        if not line:
            return self.flush()
        if line.startswith(COMMENT_PREFIX):
            return None
        name, _, value = line.partition(FIELD_SEPARATOR)
        value = value.removeprefix(" ")
        if name == "data":
            self.data.append(value)
        elif name == "event":
            self.event = value
        elif name == "id":
            self.event_id = value
        return None

    def flush(self) -> SseMessage | None:
        message = SseMessage(data="\n".join(self.data), event=self.event, event_id=self.event_id) if self.data else None
        self.data, self.event, self.event_id = [], None, None
        return message


async def parse_sse(lines: AsyncIterator[str]) -> AsyncIterator[SseMessage]:
    buffer = SseBuffer()
    async for raw in lines:
        message = buffer.feed(raw.rstrip("\r"))
        if message is not None:
            yield message
    tail = buffer.flush()
    if tail is not None:
        yield tail
