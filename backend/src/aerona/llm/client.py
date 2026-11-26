import asyncio
import contextlib
import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from aerona.catalog.providers import ANSWER_DESCRIPTION, ANSWER_INSTRUCTION, ANSWER_RECORDED, ANSWER_TOOL, ROLE_LABELS
from aerona.constants.agents import ERROR_REASON_CHARS
from aerona.constants.llm import RETRY_KIND
from aerona.core.grammar import several
from aerona.domain.enums.providers import ModelRole
from aerona.events.kinds import EventKind
from aerona.llm.backends.base import RunEnd, RunRequest, StopReason
from aerona.llm.content import AgentWatch, ImagePart, ModelCapabilities
from aerona.llm.errors import LlmDisabledError, LlmError, LlmPermanentError, LlmTimeoutError, LlmTransientError, LlmUnavailableError
from aerona.llm.events import ReplyEnded, RunEvent, ToolCalled, ToolFinished, ToolPreparing
from aerona.llm.json_text import first_json_value
from aerona.llm.records import AgentRun, CallKind, CallOutcome, CallRecord, Usage
from aerona.llm.routes import ModelRoute, NoRoutes, RouteBook
from aerona.llm.stream import StreamPublish, StreamReporter, current_actor, mute
from aerona.llm.token_count import TokenMeter, as_text, tool_text
from aerona.llm.tools import AgentTool, ToolReply
from aerona.rules.registry import Rules
from aerona.rules.registry.model import ModelRules

LOGGER = logging.getLogger(__name__)
ROOT_FIELD = "(root)"
NO_MODEL_NOTE = "No model is set for this role."
UNCHECKED_NOTE = "Check this model under Providers to learn whether it sees pictures."
UNSEEN_NOTE = "The check found that this model does not see pictures."
MetricsSink = Callable[[CallRecord], Awaitable[None]]
TEXT_ROLES = (ModelRole.WORLD_AGENTS, ModelRole.WRITING, ModelRole.CONVERSATION)


def field_paths(error: ValidationError, limit: int) -> str:
    paths = [".".join(str(part) for part in item["loc"]) or ROOT_FIELD for item in error.errors()]
    return ", ".join(dict.fromkeys(paths[:limit]))


class RulesProvider(Protocol):
    @property
    def current(self) -> Rules: ...


async def discard_metrics(_record: CallRecord) -> None:
    return None


def retry_wait_seconds(rules: ModelRules, failure_number: int) -> int:
    waits = (rules.retry_wait_1, rules.retry_wait_2, rules.retry_wait_3)
    return waits[min(failure_number, len(waits)) - 1]


@dataclass
class RunTrack:
    reporter: StreamReporter
    meter: TokenMeter
    watch: AgentWatch | None
    stop: asyncio.Event = field(default_factory=asyncio.Event)
    texts: list[str] = field(default_factory=list)
    prepared: defaultdict[str, deque[str]] = field(default_factory=lambda: defaultdict(deque))
    calls: int = 0
    queue: asyncio.Queue[RunEvent | None] = field(default_factory=asyncio.Queue)

    def sink(self, event: RunEvent) -> None:
        self.reporter.feed(event)
        self.meter.read(event)
        if isinstance(event, ToolPreparing) and event.call_id:
            self.prepared[event.tool].append(event.call_id)
        if self.watch is not None:
            self.queue.put_nowait(event)

    def call_id(self, tool: str) -> str:
        pending = self.prepared[tool]
        self.calls += 1
        return pending.popleft() if pending else f"call_{self.calls}"

    def tracked(self, tool: AgentTool) -> AgentTool:
        async def handler(arguments: dict[str, Any]) -> ToolReply:
            call_id = self.call_id(tool.name)
            self.sink(ToolCalled(call_id, tool.name, arguments))
            reply = await tool.handler(arguments)
            self.sink(ToolFinished(call_id, tool.name, reply.text, reply.is_error))
            await self.settle()
            return reply

        return AgentTool(tool.name, tool.description, tool.input_schema, handler)

    async def settle(self) -> None:
        if self.watch is None:
            return
        while not self.queue.empty():
            event = self.queue.get_nowait()
            if event is not None:
                await self.watch.seen(event)
        if self.watch.stopped:
            self.stop.set()


@dataclass
class Answer:
    output: type[BaseModel]
    limit: int
    stop: asyncio.Event | None = None
    value: BaseModel | None = None

    async def take(self, arguments: dict[str, Any]) -> ToolReply:
        try:
            self.value = self.output.model_validate(arguments)
        except ValidationError as error:
            return ToolReply(f"The result does not fit: {field_paths(error, self.limit)}. Call answer again with every field.", is_error=True)
        if self.stop is not None:
            self.stop.set()
        return ToolReply(ANSWER_RECORDED)


class LlmClient:
    def __init__(
        self,
        rules: RulesProvider,
        enabled: bool,
        routes: RouteBook | None = None,
        metrics: MetricsSink = discard_metrics,
        publish: StreamPublish = mute,
    ) -> None:
        self._publish = publish
        self._rules = rules
        self._enabled = enabled
        self._routes = routes or NoRoutes()
        self._metrics = metrics

    @property
    def enabled(self) -> bool:
        return self._enabled and any(self._routes.routes(role) for role in TEXT_ROLES)

    def ready(self, role: ModelRole) -> bool:
        return self._enabled and bool(self._routes.routes(role))

    def model_of(self, role: ModelRole) -> str:
        routes = self._routes.routes(role)
        return routes[0].name if routes else ""

    async def capabilities(self, role: ModelRole = ModelRole.CONVERSATION) -> ModelCapabilities:
        routes = self._routes.routes(role) if self._enabled else ()
        if not routes:
            return ModelCapabilities(images=False, probed=False, note=NO_MODEL_NOTE)
        sees = routes[0].sees_images
        if sees is None:
            return ModelCapabilities(images=False, probed=False, note=UNCHECKED_NOTE)
        return ModelCapabilities(images=sees, probed=True, note="" if sees else UNSEEN_NOTE)

    async def structured[T: BaseModel](
        self,
        label: str,
        system_prompt: str,
        prompt: str,
        *,
        output: type[T],
        attempts: int | None = None,
        schema: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
        role: ModelRole = ModelRole.WRITING,
    ) -> T:
        model_rules = self._rules.current.model
        output_schema = schema or output.model_json_schema()
        system = f"{system_prompt}\n\n{ANSWER_INSTRUCTION}"

        async def attempt(route: ModelRoute, usage: Usage) -> T:
            reporter = StreamReporter(self._publish, self._rules.current.server, None, label)
            track = RunTrack(reporter, TokenMeter(system, as_text(output_schema), prompt), None)
            answer = Answer(output, self._rules.current.metrics.missing_fields_listed, track.stop)
            tool = AgentTool(ANSWER_TOOL, ANSWER_DESCRIPTION, output_schema, answer.take)
            request = RunRequest(system, prompt, (track.tracked(tool),), route.model, model_rules.structured_max_steps)
            try:
                end = await self._run(route, request, track, usage)
            except BaseException as error:
                reporter.close(str(error) or type(error).__name__)
                raise
            reporter.close()
            value = answer.value if answer.value is not None else self._answer_in_text(track.texts, output, label)
            if not isinstance(value, output):
                raise LlmTransientError(f"the model ended ({end.stop}) without handing in the result")
            return value

        return await self._walk(label, CallKind.STRUCTURED, role, attempt, timeout_seconds=timeout_seconds or model_rules.structured_timeout, attempts=attempts)

    async def run_agent(
        self,
        label: str,
        system_prompt: str,
        prompt: str,
        *,
        tools: Sequence[AgentTool],
        max_turns: int | None = None,
        timeout_seconds: int | None = None,
        images: Sequence[ImagePart] = (),
        watch: AgentWatch | None = None,
        role: ModelRole = ModelRole.WORLD_AGENTS,
    ) -> AgentRun:
        model_rules = self._rules.current.model
        limit = max_turns or model_rules.agent_max_steps

        async def attempt(route: ModelRoute, usage: Usage) -> AgentRun:
            reporter = StreamReporter(self._publish, self._rules.current.server, current_actor.get(), label)
            track = RunTrack(reporter, TokenMeter(system_prompt, *(tool_text(tool) for tool in tools), prompt), watch)
            shown = tuple(images) if route.sees_images else ()
            request = RunRequest(system_prompt, prompt, tuple(track.tracked(tool) for tool in tools), route.model, limit, shown)
            try:
                end = await self._run(route, request, track, usage)
            finally:
                reporter.close()
            completed = end.stop is StopReason.COMPLETED
            if not completed:
                LOGGER.warning("Agent turn %s ended unfinished (%s) after %s model replies; step limit %s", label, end.stop, usage.turns, limit)
            return AgentRun(text="\n".join(track.texts), usage=usage, completed=completed, stop_reason=end.stop.value)

        return await self._walk(label, CallKind.AGENT, role, attempt, timeout_seconds=timeout_seconds or model_rules.agent_timeout, attempts=1)

    async def _run(self, route: ModelRoute, request: RunRequest, track: RunTrack, usage: Usage) -> RunEnd:
        backend = await route.open()

        def sink(event: RunEvent) -> None:
            track.sink(event)
            if isinstance(event, ReplyEnded) and event.text:
                track.texts.append(event.text)

        try:
            end = await backend.run(request, sink, track.stop)
        finally:
            usage.count(track.meter)
            usage.turns += track.meter.replies
        await track.settle()
        return end

    @staticmethod
    def _answer_in_text[T: BaseModel](texts: list[str], output: type[T], label: str) -> T | None:
        for text in reversed(texts):
            with contextlib.suppress(json.JSONDecodeError, ValidationError):
                return output.model_validate(first_json_value(text))
        LOGGER.debug("No result in the text of %s", label)
        return None

    def _announce_retry(self, label: str, attempt: int, total: int, reason: str, wait: int) -> None:
        actor = current_actor.get()
        channel = {"channel": actor.channel} if actor is not None and actor.channel else {}
        self._publish(
            EventKind.AGENT_RETRY,
            {
                **channel,
                "actor": actor.name if actor is not None else label,
                "kind": RETRY_KIND,
                "attempt": attempt,
                "total": total,
                "reason": reason[:ERROR_REASON_CHARS],
                "wait_s": wait,
                "kept_steps": 0,
            },
        )

    async def _walk[R](
        self,
        label: str,
        kind: CallKind,
        role: ModelRole,
        attempt: Callable[[ModelRoute, Usage], Awaitable[R]],
        *,
        timeout_seconds: int,
        attempts: int | None,
    ) -> R:
        routes = self._routes.routes(role) if self._enabled else ()
        if not routes:
            record = CallRecord(label=label, kind=kind, model="", outcome=CallOutcome.DISABLED)
            await self._metrics(record)
            raise LlmDisabledError(f"No model is set for {ROLE_LABELS[role].lower()} ({label}).")
        failure: LlmError | None = None
        for route in routes:
            try:
                return await self._with_retries(label, kind, route, attempt, timeout_seconds=timeout_seconds, attempts=attempts)
            except (LlmTransientError, LlmUnavailableError, LlmPermanentError) as error:
                failure = error
                LOGGER.warning("Model %s could not serve %s, trying the next one: %s", route.name, label, error)
        assert failure is not None
        raise failure

    async def _with_retries[R](
        self,
        label: str,
        kind: CallKind,
        route: ModelRoute,
        attempt: Callable[[ModelRoute, Usage], Awaitable[R]],
        *,
        timeout_seconds: int,
        attempts: int | None,
    ) -> R:
        record = CallRecord(label=label, kind=kind, model=route.name)
        started = time.monotonic()
        model_rules = self._rules.current.model
        total = attempts or model_rules.retry_attempts
        error_chars = self._rules.current.metrics.error_chars
        try:
            for number in range(1, total + 1):
                record.attempts = number
                try:
                    value = await asyncio.wait_for(attempt(route, record.usage), timeout=timeout_seconds)
                    record.outcome = CallOutcome.OK
                    return value
                except TimeoutError as error:
                    record.outcome = CallOutcome.TIMEOUT
                    last: LlmError = LlmTimeoutError(f"{label} timed out after {timeout_seconds}s")
                    last.__cause__ = error
                except LlmTransientError as error:
                    record.outcome = CallOutcome.FAILED
                    last = error
                record.error = str(last)[:error_chars]
                if number < total:
                    wait = retry_wait_seconds(model_rules, number)
                    self._announce_retry(label, number + 1, total, record.error, wait)
                    await asyncio.sleep(wait)
            LOGGER.error("Model call %s (%s, %s) failed: %s", label, route.name, several(total, "attempt", "attempts"), record.error)
            raise last
        except (LlmPermanentError, LlmUnavailableError) as error:
            record.outcome = CallOutcome.FAILED
            record.error = str(error)[:error_chars]
            LOGGER.error("Model call %s (%s) failed: %s", label, route.name, record.error)
            raise
        finally:
            record.duration_seconds = time.monotonic() - started
            await self._metrics(record)
