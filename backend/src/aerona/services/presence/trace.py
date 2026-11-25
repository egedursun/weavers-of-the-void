from collections.abc import Mapping
from typing import Any

from claude_agent_sdk import AssistantMessage, TextBlock, ThinkingBlock, ToolResultBlock, ToolUseBlock, UserMessage

from aerona.db.repositories.presence import add_event
from aerona.db.session import Database
from aerona.domain.enums.presence import PresenceEventKind
from aerona.llm.stream import result_text, short_tool_name
from aerona.services.divine_will.trace import outcome_line

E = PresenceEventKind


class ExchangeTrace:
    def __init__(self, database: Database, exchange_id: int) -> None:
        self.database = database
        self.exchange_id = exchange_id

    async def add(self, kind: PresenceEventKind, *, tool: str = "", payload: Mapping[str, Any] | None = None) -> int:
        async with self.database.write() as session:
            row = await add_event(session, self.exchange_id, kind, tool=tool, payload=payload)
            return row.ordinal


class ExchangeWatch:
    def __init__(self, trace: ExchangeTrace) -> None:
        self.trace = trace
        self.calls: dict[str, str] = {}
        self.final_parts: list[str] = []
        self.replies = 0

    @property
    def stopped(self) -> bool:
        return False

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
            await self.trace.add(E.TEXT, payload={"text": block.text})
        elif isinstance(block, ThinkingBlock) and block.thinking.strip():
            await self.trace.add(E.THOUGHT, payload={"text": block.thinking})
        elif isinstance(block, ToolUseBlock):
            tool = short_tool_name(block.name)
            self.calls[block.id] = tool
            self.final_parts = []
            await self.trace.add(E.TOOL_CALL, tool=tool, payload={"call_id": block.id, "arguments": dict(block.input or {})})

    async def result(self, call_id: str, text: str, is_error: bool) -> None:
        tool = self.calls.pop(call_id, "")
        payload = {"call_id": call_id, "text": text, "is_error": is_error, "outcome": outcome_line(text, is_error)}
        await self.trace.add(E.TOOL_RESULT, tool=tool, payload=payload)
