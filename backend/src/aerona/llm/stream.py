import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from aerona.constants.agents import TOOL_RESULT_CHARS
from aerona.domain.enums.node import ActorKind
from aerona.events.kinds import EventKind
from aerona.llm.events import ReplyEnded, RunEvent, TextDelta, ToolCalled, ToolFinished, ToolPreparing, ToolWriting
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
class ReporterState:
    seen: dict[str, int] = field(default_factory=dict)
    reported: dict[str, int] = field(default_factory=dict)
    text_buffer: str = ""
    text_chars: int = 0
    last_text_flush: float = float("-inf")
    chars: int = 0
    last_progress: float = float("-inf")
    progress_sent: bool = False


class StreamReporter:
    def __init__(self, publish: StreamPublish, rules: ServerRules, actor: StreamActor | None, label: str, clock: Clock = time.monotonic) -> None:
        self._publish = publish
        self._rules = rules
        self._actor = actor
        self._label = label
        self._clock = clock
        self._stream_id = uuid.uuid4().hex
        self._state = ReporterState()

    def feed(self, event: RunEvent) -> None:
        match event:
            case TextDelta(text=text):
                self._text(text)
            case ToolPreparing(call_id=call_id, tool=tool):
                self._preparing(call_id, tool)
            case ToolWriting(call_id=call_id, tool=tool, chars=chars):
                self._writing(call_id, tool, chars)
            case ReplyEnded(text=text):
                self._ended(text)
            case ToolCalled(call_id=call_id, tool=tool, input=arguments):
                self._called(call_id, tool, arguments)
            case ToolFinished(call_id=call_id, tool=tool, text=text, is_error=is_error):
                self._finished(call_id, tool, text, is_error)
            case _:
                return

    def close(self, error: str | None = None) -> None:
        state = self._state
        if self._actor is None:
            if state.progress_sent or state.chars:
                self._emit_writing(finished=True, error=error)
            return
        self._flush_text()

    def _emit(self, kind: EventKind, **fields: Any) -> None:
        actor = self._actor
        self._publish(kind, {**(actor.fields() if actor is not None else {}), **fields})

    def _text(self, text: str) -> None:
        state = self._state
        state.chars += len(text)
        if self._actor is None:
            self._maybe_writing()
            return
        state.text_buffer += text
        if self._clock() - state.last_text_flush >= self._rules.stream_emit_interval_ms / 1000:
            self._flush_text()

    def _preparing(self, call_id: str, tool: str) -> None:
        if self._actor is None:
            return
        self._flush_text()
        self._emit(EventKind.AGENT_TOOL_PREPARING, tool=tool, call_id=call_id)

    def _writing(self, call_id: str, tool: str, chars: int) -> None:
        state = self._state
        state.chars += max(0, chars - state.seen.get(call_id, 0))
        state.seen[call_id] = chars
        if self._actor is None:
            self._maybe_writing()
            return
        if chars - state.reported.get(call_id, 0) >= self._rules.tool_write_step_chars:
            state.reported[call_id] = chars
            self._emit(EventKind.AGENT_TOOL_WRITING, tool=tool, call_id=call_id, chars=chars)

    def _ended(self, text: str) -> None:
        self._flush_text()
        if self._actor is not None and text.strip():
            self._emit(EventKind.AGENT_THOUGHT, text=text)

    def _called(self, call_id: str, tool: str, arguments: dict[str, Any]) -> None:
        actor = self._actor
        if actor is None:
            return
        self._emit(EventKind.AGENT_TOOL_CALLED, tool=tool, call_id=call_id, input=arguments, read_only=tool in actor.read_only_tools)

    def _finished(self, call_id: str, tool: str, text: str, is_error: bool) -> None:
        actor = self._actor
        if actor is None:
            return
        self._emit(EventKind.AGENT_TOOL_RESULT, tool=tool, call_id=call_id, text=text[:TOOL_RESULT_CHARS], error=is_error, quiet=tool in actor.read_only_tools)

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
