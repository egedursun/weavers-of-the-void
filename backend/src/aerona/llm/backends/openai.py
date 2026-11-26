import asyncio
import base64
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from openai import APIConnectionError, APIStatusError, AsyncOpenAI, OpenAIError

from aerona.constants.llm import TRANSIENT_HTTP_STATUSES
from aerona.llm.backends.base import RunEnd, RunRequest, StopReason
from aerona.llm.content import ImagePart
from aerona.llm.errors import LlmError, LlmPermanentError, LlmTransientError, LlmUnavailableError
from aerona.llm.events import EventSink, ReplyEnded, TextDelta, ThoughtDelta, ToolPreparing, ToolWriting
from aerona.llm.tools import AgentTool, ToolReply

REFUSED_STATUSES = frozenset({401, 403})
BROKEN_ARGUMENTS = "The arguments were not valid JSON."


def classified(error: OpenAIError) -> LlmError:
    if isinstance(error, APIStatusError):
        if error.status_code in REFUSED_STATUSES:
            return LlmUnavailableError(f"the provider refused the key ({error.status_code})")
        if error.status_code in TRANSIENT_HTTP_STATUSES or error.status_code >= 500:
            return LlmTransientError(f"the provider answered {error.status_code}: {error.message}")
        return LlmPermanentError(f"the provider answered {error.status_code}: {error.message}")
    if isinstance(error, APIConnectionError):
        return LlmUnavailableError(f"the provider could not be reached: {error}")
    return LlmTransientError(str(error) or type(error).__name__)


def user_content(prompt: str, images: Sequence[ImagePart]) -> str | list[dict[str, Any]]:
    if not images:
        return prompt
    parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images:
        encoded = base64.b64encode(image.data).decode("ascii")
        parts.append({"type": "image_url", "image_url": {"url": f"data:{image.media_type};base64,{encoded}"}})
    return parts


def function_of(tool: AgentTool) -> dict[str, Any]:
    return {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.input_schema}}


@dataclass
class PendingCall:
    call_id: str = ""
    name: str = ""
    arguments: str = ""


@dataclass
class Reply:
    text: list[str] = field(default_factory=list)
    thoughts: list[str] = field(default_factory=list)
    calls: dict[int, PendingCall] = field(default_factory=dict)


class OpenAIBackend:
    def __init__(self, client: AsyncOpenAI, model_prefix: str = "") -> None:
        self._client = client
        self._prefix = model_prefix

    async def models(self) -> list[str]:
        try:
            page = await self._client.models.list(extra_query={"provider": self._prefix.rstrip("/")} if self._prefix else None)
        except OpenAIError as error:
            raise classified(error) from error
        return sorted(item.id.removeprefix(self._prefix) for item in page.data)

    async def close(self) -> None:
        await self._client.close()

    async def run(self, request: RunRequest, events: EventSink, stop: asyncio.Event) -> RunEnd:
        tools = {tool.name: tool for tool in request.tools}
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": request.system},
            {"role": "user", "content": user_content(request.prompt, request.images)},
        ]
        turns = 0
        while True:
            if stop.is_set():
                return RunEnd(StopReason.STOPPED, turns)
            if turns >= request.max_turns:
                return RunEnd(StopReason.STEP_LIMIT, turns)
            reply = await self._reply(request.model, messages, list(tools.values()), events)
            turns += 1
            events(ReplyEnded("".join(reply.text), "".join(reply.thoughts)))
            if not reply.calls:
                return RunEnd(StopReason.COMPLETED, turns)
            calls = [reply.calls[index] for index in sorted(reply.calls)]
            for index, call in enumerate(calls):
                call.call_id = call.call_id or f"call_{turns}_{index}"
            messages.append(
                {
                    "role": "assistant",
                    "content": "".join(reply.text) or None,
                    "tool_calls": [{"id": call.call_id, "type": "function", "function": {"name": call.name, "arguments": call.arguments}} for call in calls],
                }
            )
            for call in calls:
                answer = await self._answer(tools, call)
                messages.append({"role": "tool", "tool_call_id": call.call_id, "content": answer.text})
                if stop.is_set():
                    return RunEnd(StopReason.STOPPED, turns)

    async def _answer(self, tools: dict[str, AgentTool], call: PendingCall) -> ToolReply:
        tool = tools.get(call.name)
        if tool is None:
            return ToolReply(f"No tool is named {call.name}.", is_error=True)
        try:
            arguments = json.loads(call.arguments or "{}")
        except json.JSONDecodeError:
            return ToolReply(BROKEN_ARGUMENTS, is_error=True)
        return await tool.handler(arguments if isinstance(arguments, dict) else {})

    async def _reply(self, model: str, messages: list[dict[str, Any]], tools: list[AgentTool], events: EventSink) -> Reply:
        reply = Reply()
        options: dict[str, Any] = {"tools": [function_of(tool) for tool in tools]} if tools else {}
        try:
            create: Any = self._client.chat.completions.create
            stream = await create(model=f"{self._prefix}{model}", messages=messages, stream=True, **options)
            async for chunk in stream:
                for choice in chunk.choices:
                    self._read(choice.delta, reply, events)
        except OpenAIError as error:
            raise classified(error) from error
        return reply

    @staticmethod
    def _read(delta: Any, reply: Reply, events: EventSink) -> None:
        thought = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
        if isinstance(thought, str) and thought:
            reply.thoughts.append(thought)
            events(ThoughtDelta(thought))
        if delta.content:
            reply.text.append(delta.content)
            events(TextDelta(delta.content))
        for part in delta.tool_calls or ():
            call = reply.calls.setdefault(part.index, PendingCall())
            fresh = not call.name
            if part.id:
                call.call_id = part.id
            if part.function is not None:
                call.name += part.function.name or ""
                call.arguments += part.function.arguments or ""
            if fresh and call.name:
                events(ToolPreparing(call.call_id, call.name))
            elif call.name:
                events(ToolWriting(call.call_id, call.name, len(call.arguments)))
