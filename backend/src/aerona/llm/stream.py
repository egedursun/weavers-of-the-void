import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import AssistantMessage, StreamEvent, TextBlock, ToolResultBlock, ToolUseBlock, UserMessage

from aerona.constants.agents import TOOL_RESULT_CHARS
from aerona.constants.llm import TOOL_NAME_PREFIX
from aerona.domain.enums.node import ActorKind
from aerona.events.kinds import EventKind
from aerona.rules.registry.server import ServerRules

StreamPublish = Callable[[EventKind, dict[str, Any]], None]
Clock = Callable[[], float]


def mute(kind: EventKind, payload: dict[str, Any]) -> None:
    del kind, payload


@dataclass(frozen=True)
class StreamActor:
    kind: ActorKind
    id: int
    name: str
    read_only_tools: frozenset[str] = frozenset()
    channel: str = ""

    def fields(self) -> dict[str, Any]:
        found: dict[str, Any] = {"actor_kind": self.kind.value, "actor_id": self.id, "actor_name": self.name}
        if self.channel:
            found["channel"] = self.channel
        return found


current_actor: ContextVar[StreamActor | None] = ContextVar("current_stream_actor", default=None)


@dataclass
class ToolBlock:
    call_id: str
    tool: str
    chars: int = 0
    reported: int = 0


@dataclass
class ReporterState:
    blocks: dict[int, ToolBlock] = field(default_factory=dict)
    tools: dict[str, str] = field(default_factory=dict)
    text_buffer: str = ""
    text_chars: int = 0
    last_text_flush: float = float("-inf")
    chars: int = 0
    last_progress: float = float("-inf")
    progress_sent: bool = False


def short_tool_name(name: str) -> str:
    return name.removeprefix(TOOL_NAME_PREFIX)


def result_text(content: str | list[dict[str, Any]] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))


class StreamReporter:
    def __init__(self, publish: StreamPublish, rules: ServerRules, actor: StreamActor | None, label: str, clock: Clock = time.monotonic) -> None:
        self._publish = publish
        self._rules = rules
        self._actor = actor
        self._label = label
        self._clock = clock
        self._stream_id = uuid.uuid4().hex
        self._state = ReporterState()

    def feed(self, message: object) -> None:
        if isinstance(message, StreamEvent):
            if message.parent_tool_use_id is None:
                self._partial(message.event)
        elif self._actor is not None and isinstance(message, AssistantMessage):
            self._assistant(message)
        elif self._actor is not None and isinstance(message, UserMessage):
            self._user(message)

    def close(self, error: str | None = None) -> None:
        state = self._state
        if self._actor is None:
            if state.progress_sent or state.chars:
                self._emit_writing(finished=True, error=error)
            return
        self._flush_text()

    def _actor_fields(self) -> dict[str, Any]:
        actor = self._actor
        if actor is None:
            return {}
        return actor.fields()

    def _emit(self, kind: EventKind, **fields: Any) -> None:
        self._publish(kind, {**self._actor_fields(), **fields})

    def _partial(self, event: dict[str, Any]) -> None:
        kind = event.get("type")
        index = int(event.get("index", 0))
        if kind == "content_block_start":
            self._block_started(index, event.get("content_block") or {})
        elif kind == "content_block_delta":
            self._delta(index, event.get("delta") or {})
        elif kind == "content_block_stop":
            self._flush_text()
            self._state.blocks.pop(index, None)

    def _block_started(self, index: int, block: dict[str, Any]) -> None:
        if block.get("type") != "tool_use" or self._actor is None:
            return
        tool = short_tool_name(str(block.get("name", "")))
        call_id = str(block.get("id", ""))
        self._state.blocks[index] = ToolBlock(call_id, tool)
        self._state.tools[call_id] = tool
        self._emit(EventKind.AGENT_TOOL_PREPARING, tool=tool, call_id=call_id)

    def _delta(self, index: int, delta: dict[str, Any]) -> None:
        state = self._state
        delta_type = delta.get("type")
        if delta_type == "text_delta":
            text = str(delta.get("text", ""))
            state.chars += len(text)
            if self._actor is None:
                self._maybe_writing()
                return
            state.text_buffer += text
            if self._clock() - state.last_text_flush >= self._rules.stream_emit_interval_ms / 1000:
                self._flush_text()
        elif delta_type == "input_json_delta":
            size = len(str(delta.get("partial_json", "")))
            state.chars += size
            if self._actor is None:
                self._maybe_writing()
                return
            block = state.blocks.get(index)
            if block is not None:
                block.chars += size
                if block.chars - block.reported >= self._rules.tool_write_step_chars:
                    block.reported = block.chars
                    self._emit(EventKind.AGENT_TOOL_WRITING, tool=block.tool, call_id=block.call_id, chars=block.chars)

    def _flush_text(self) -> None:
        state = self._state
        if not state.text_buffer:
            return
        state.text_chars += len(state.text_buffer)
        self._emit(EventKind.AGENT_STREAM, text=state.text_buffer, chars=state.text_chars)
        state.text_buffer = ""
        state.last_text_flush = self._clock()

    def _maybe_writing(self) -> None:
        if self._clock() - self._state.last_progress >= self._rules.writing_emit_interval_ms / 1000:
            self._emit_writing(finished=False, error=None)

    def _emit_writing(self, *, finished: bool, error: str | None) -> None:
        state = self._state
        state.progress_sent = True
        state.last_progress = self._clock()
        status = None if not finished else ("error" if error else "ok")
        self._publish(
            EventKind.AGENT_WRITING,
            {"who": self._label, "stream_id": self._stream_id, "chars": state.chars, "finished": finished, "status": status, "error": error},
        )

    def _assistant(self, message: AssistantMessage) -> None:
        if message.parent_tool_use_id is not None:
            return
        actor = self._actor
        for block in message.content:
            if isinstance(block, TextBlock) and block.text.strip():
                self._flush_text()
                self._emit(EventKind.AGENT_THOUGHT, text=block.text)
            elif isinstance(block, ToolUseBlock):
                tool = short_tool_name(block.name)
                self._state.tools[block.id] = tool
                read_only = actor is not None and tool in actor.read_only_tools
                self._emit(EventKind.AGENT_TOOL_CALLED, tool=tool, call_id=block.id, input=block.input, read_only=read_only)

    def _user(self, message: UserMessage) -> None:
        if not isinstance(message.content, list):
            return
        actor = self._actor
        for block in message.content:
            if isinstance(block, ToolResultBlock):
                tool = self._state.tools.get(block.tool_use_id, "")
                quiet = actor is not None and tool in actor.read_only_tools
                self._emit(
                    EventKind.AGENT_TOOL_RESULT,
                    tool=tool,
                    call_id=block.tool_use_id,
                    text=result_text(block.content)[:TOOL_RESULT_CHARS],
                    error=bool(block.is_error),
                    quiet=quiet,
                )
