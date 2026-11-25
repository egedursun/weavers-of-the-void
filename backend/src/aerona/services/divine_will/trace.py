import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import AssistantMessage, TextBlock, ThinkingBlock, ToolResultBlock, ToolUseBlock, UserMessage

from aerona.db.repositories.divine_will import add_event
from aerona.db.session import Database
from aerona.domain.enums.divine_will import CycleEventKind
from aerona.llm.stream import result_text, short_tool_name
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.framework import WillResult

NOTICE_KEY = "notice"
REASON_KEY = "reason"
HEAD_KEYS = frozenset({"total", "shown", "page", "next", "handle"})


def argument_key(arguments: Mapping[str, Any]) -> str:
    return json.dumps(dict(arguments), sort_keys=True, default=str)


def paged_head(line: str) -> dict[str, Any] | None:
    if not line.startswith("{"):
        return None
    try:
        found = json.loads(line)
    except ValueError:
        return None
    return found if isinstance(found, dict) and set(found) >= HEAD_KEYS else None


def outcome_line(text: str, is_error: bool) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    head = paged_head(lines[0]) if lines else None
    body = lines[1:] if head is not None else lines
    first = body[0] if body else ""
    if head is None:
        return first if first or not is_error else "the tool refused without a reason"
    more = "; further pages remain" if head.get("next") else ""
    summary = f"page {head.get('page')} shows {head.get('shown')} of {head.get('total')}{more}"
    return f"{summary}; {first}" if first else summary


@dataclass
class Stashed:
    tool: str
    arguments: str
    result: WillResult


@dataclass
class OutcomeBook:
    items: list[Stashed] = field(default_factory=list)
    paused: bool = False
    refused: bool = False

    def stash(self, tool: str, arguments: Mapping[str, Any], result: WillResult) -> None:
        self.items.append(Stashed(tool, argument_key(arguments), result))
        if result.pause:
            self.paused = True

    def take(self, tool: str, arguments: Mapping[str, Any]) -> WillResult | None:
        wanted = argument_key(arguments)
        exact = [index for index, item in enumerate(self.items) if item.tool == tool and item.arguments == wanted]
        loose = [index for index, item in enumerate(self.items) if item.tool == tool]
        chosen = exact or loose
        return self.items.pop(chosen[0]).result if chosen else None

    def rest(self) -> list[Stashed]:
        found, self.items = self.items, []
        return found


class CycleTrace:
    def __init__(self, database: Database, cycle_id: int) -> None:
        self.database = database
        self.cycle_id = cycle_id

    async def add(self, kind: CycleEventKind, *, tool: str = "", payload: Mapping[str, Any] | None = None, handle: str = "") -> int:
        async with self.database.write() as session:
            row = await add_event(session, self.cycle_id, kind, tool=tool, payload=payload, handle=handle)
            return row.ordinal


PauseHandler = Callable[[str, WillResult], Awaitable[None]]


class CycleWatch:
    def __init__(self, trace: CycleTrace, book: OutcomeBook, on_pause: PauseHandler) -> None:
        self.trace = trace
        self.book = book
        self.on_pause = on_pause
        self.calls: dict[str, tuple[str, dict[str, Any]]] = {}
        self.final_parts: list[str] = []
        self.replies = 0

    @property
    def stopped(self) -> bool:
        return self.book.refused

    @property
    def final_text(self) -> str:
        return "\n\n".join(part.strip() for part in self.final_parts if part.strip())

    async def seen(self, message: object) -> None:
        if isinstance(message, AssistantMessage) and message.parent_tool_use_id is None:
            self.replies += 1
            for block in message.content:
                await self.block(block)
        elif isinstance(message, UserMessage) and message.parent_tool_use_id is None and isinstance(message.content, list):
            for part in message.content:
                if isinstance(part, ToolResultBlock):
                    await self.result(part.tool_use_id, result_text(part.content), bool(part.is_error))

    async def block(self, block: object) -> None:
        if isinstance(block, TextBlock) and block.text.strip():
            self.final_parts.append(block.text)
            await self.trace.add(CycleEventKind.TEXT, payload={"text": block.text})
        elif isinstance(block, ThinkingBlock) and block.thinking.strip():
            await self.trace.add(CycleEventKind.THOUGHT, payload={"text": block.thinking})
        elif isinstance(block, ToolUseBlock):
            tool = short_tool_name(block.name)
            arguments = dict(block.input or {})
            self.calls[block.id] = (tool, arguments)
            self.final_parts = []
            await self.trace.add(CycleEventKind.TOOL_CALL, tool=tool, payload={"call_id": block.id, "arguments": arguments})

    async def result(self, call_id: str, text: str, is_error: bool) -> None:
        tool, arguments = self.calls.pop(call_id, ("", {}))
        await self.record(call_id, tool, text, is_error, self.book.take(tool, arguments))

    async def record(self, call_id: str, tool: str, text: str, is_error: bool, stashed: WillResult | None) -> None:
        payload: dict[str, Any] = {"call_id": call_id, "text": text, "is_error": is_error, "outcome": outcome_line(text, is_error)}
        details = dict(stashed.payload) if stashed is not None else {}
        if details:
            payload["details"] = details
        await self.trace.add(CycleEventKind.TOOL_RESULT, tool=tool, payload=payload, handle=stashed.handle if stashed is not None else "")
        if stashed is None:
            return
        if tool == DivineWillToolId.SUGGEST_MODE.value or NOTICE_KEY in details:
            await self.trace.add(
                CycleEventKind.NOTICE, tool=tool, payload={**details, "text": str(details.get(REASON_KEY) or details.get("text") or stashed.text)}
            )
        if stashed.pause:
            await self.on_pause(tool, stashed)

    async def flush(self) -> None:
        for item in self.book.rest():
            await self.record("", item.tool, item.result.text, item.result.is_error, item.result)
