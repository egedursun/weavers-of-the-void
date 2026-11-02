import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, CLIConnectionError, ProcessError, ResultMessage, SdkMcpTool, TextBlock, query
from pydantic import BaseModel, ValidationError

from aerona.constants.agents import ERROR_REASON_CHARS
from aerona.constants.llm import HAIKU_MODEL_ID, RETRY_KIND, TRANSIENT_HTTP_STATUSES
from aerona.events.kinds import EventKind
from aerona.llm.errors import LlmDisabledError, LlmPermanentError, LlmTimeoutError, LlmTransientError
from aerona.llm.json_text import first_json_value
from aerona.llm.records import AgentRun, CallKind, CallOutcome, CallRecord, Usage
from aerona.llm.sandbox import build_options
from aerona.llm.stream import StreamPublish, StreamReporter, current_actor, mute
from aerona.rules.registry import Rules
from aerona.rules.registry.model import ModelRules

LOGGER = logging.getLogger(__name__)
ROOT_FIELD = "(root)"
MetricsSink = Callable[[CallRecord], Awaitable[None]]
QueryFunction = Callable[..., AsyncIterator[Any]]


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


class LlmClient:
    def __init__(
        self,
        rules: RulesProvider,
        enabled: bool,
        metrics: MetricsSink = discard_metrics,
        query_function: QueryFunction = query,
        publish: StreamPublish = mute,
    ) -> None:
        self._publish = publish
        self._rules = rules
        self._enabled = enabled
        self._metrics = metrics
        self._query = query_function

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def model(self) -> str:
        return HAIKU_MODEL_ID

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
    ) -> T:
        model_rules = self._rules.current.model
        options = build_options(system_prompt, model_rules.structured_max_steps, output_schema=schema or output.model_json_schema())

        async def attempt(usage: Usage) -> T:
            reporter = StreamReporter(self._publish, self._rules.current.server, None, label)
            try:
                payload = await self._collect_structured(prompt, options, usage, reporter)
            except BaseException as error:
                reporter.close(str(error) or type(error).__name__)
                raise
            reporter.close()
            try:
                return output.model_validate(payload)
            except ValidationError as error:
                paths = field_paths(error, self._rules.current.metrics.missing_fields_listed)
                LOGGER.warning("Model output for %s missed or broke required fields: %s", label, paths)
                raise LlmTransientError(f"structured output did not match schema: {error.error_count()} error(s) in {paths}") from error

        return await self._with_retries(label, CallKind.STRUCTURED, attempt, timeout_seconds or model_rules.structured_timeout, attempts)

    async def run_agent(
        self,
        label: str,
        system_prompt: str,
        prompt: str,
        *,
        tools: list[SdkMcpTool[Any]],
        max_turns: int | None = None,
        timeout_seconds: int | None = None,
    ) -> AgentRun:
        model_rules = self._rules.current.model
        options = build_options(system_prompt, max_turns or model_rules.agent_max_steps, tools=tools)

        limit = max_turns or model_rules.agent_max_steps

        async def attempt(usage: Usage) -> AgentRun:
            reporter = StreamReporter(self._publish, self._rules.current.server, current_actor.get(), label)
            try:
                run = await self._collect_agent(prompt, options, usage, reporter)
            finally:
                reporter.close()
            if not run.completed:
                LOGGER.warning("Agent turn %s ended unfinished (%s) after %s model replies; step limit %s", label, run.stop_reason, usage.turns, limit)
            return run

        return await self._with_retries(label, CallKind.AGENT, attempt, timeout_seconds or model_rules.agent_timeout, 1)

    async def _collect_structured(self, prompt: str, options: ClaudeAgentOptions, usage: Usage, reporter: StreamReporter) -> Any:
        result: ResultMessage | None = None
        async for message in self._query(prompt=prompt, options=options):
            reporter.feed(message)
            if isinstance(message, ResultMessage):
                result = message
        if result is None:
            raise LlmTransientError("model returned no result")
        usage.absorb(result.usage, result.total_cost_usd, result.num_turns)
        self._raise_for_result(result)
        if result.structured_output is not None:
            return result.structured_output
        if result.result:
            try:
                return first_json_value(result.result)
            except json.JSONDecodeError as error:
                raise LlmTransientError("model returned unparseable output") from error
        raise LlmTransientError("model returned empty output")

    async def _collect_agent(self, prompt: str, options: ClaudeAgentOptions, usage: Usage, reporter: StreamReporter) -> AgentRun:
        texts: list[str] = []
        result: ResultMessage | None = None
        async for message in self._query(prompt=prompt, options=options):
            reporter.feed(message)
            if isinstance(message, AssistantMessage):
                texts.extend(block.text for block in message.content if isinstance(block, TextBlock))
            elif isinstance(message, ResultMessage):
                result = message
        if result is None:
            return AgentRun(text="\n".join(texts), usage=usage, completed=False, stop_reason=None)
        usage.absorb(result.usage, result.total_cost_usd, result.num_turns)
        return AgentRun(text="\n".join(texts), usage=usage, completed=not result.is_error, stop_reason=result.stop_reason or result.subtype)

    @staticmethod
    def _raise_for_result(result: ResultMessage) -> None:
        if not result.is_error:
            return
        status = result.api_error_status
        message = f"model error {result.subtype} {status or ''}".strip()
        if status is None or status in TRANSIENT_HTTP_STATUSES:
            raise LlmTransientError(message)
        raise LlmPermanentError(message)

    def _announce_retry(self, label: str, attempt: int, total: int, reason: str, wait: int) -> None:
        actor = current_actor.get()
        self._publish(
            EventKind.AGENT_RETRY,
            {
                "actor": actor.name if actor is not None else label,
                "kind": RETRY_KIND,
                "attempt": attempt,
                "total": total,
                "reason": reason[:ERROR_REASON_CHARS],
                "wait_s": wait,
                "kept_steps": 0,
            },
        )

    async def _with_retries[R](self, label: str, kind: CallKind, attempt: Callable[[Usage], Awaitable[R]], timeout_seconds: int, attempts: int | None) -> R:
        record = CallRecord(label=label, kind=kind, model=HAIKU_MODEL_ID)
        started = time.monotonic()
        if not self._enabled:
            record.outcome = CallOutcome.DISABLED
            await self._metrics(record)
            raise LlmDisabledError(f"LLM calls are disabled ({label}).")
        model_rules = self._rules.current.model
        total = attempts or model_rules.retry_attempts
        try:
            for number in range(1, total + 1):
                record.attempts = number
                try:
                    value = await asyncio.wait_for(attempt(record.usage), timeout=timeout_seconds)
                    record.outcome = CallOutcome.OK
                    return value
                except TimeoutError as error:
                    record.outcome = CallOutcome.TIMEOUT
                    last: Exception = LlmTimeoutError(f"{label} timed out after {timeout_seconds}s")
                    last.__cause__ = error
                except (LlmTransientError, CLIConnectionError, ProcessError) as error:
                    record.outcome = CallOutcome.FAILED
                    last = error
                record.error = str(last)[: self._rules.current.metrics.error_chars]
                if number < total:
                    wait = retry_wait_seconds(model_rules, number)
                    self._announce_retry(label, number + 1, total, record.error, wait)
                    await asyncio.sleep(wait)
            LOGGER.error("Model call %s (%s, %s attempts) failed: %s", label, HAIKU_MODEL_ID, total, record.error)
            raise last
        except LlmPermanentError as error:
            record.outcome = CallOutcome.FAILED
            record.error = str(error)[: self._rules.current.metrics.error_chars]
            LOGGER.error("Model call %s (%s) failed permanently: %s", label, HAIKU_MODEL_ID, record.error)
            raise
        finally:
            record.duration_seconds = time.monotonic() - started
            await self._metrics(record)
