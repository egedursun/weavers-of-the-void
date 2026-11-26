from collections.abc import Mapping
from typing import Any

from aerona.db.repositories.presence import add_event
from aerona.db.session import Database
from aerona.domain.enums.presence import PresenceEventKind
from aerona.llm.events import ReplyEnded, RunEvent, ToolCalled, ToolFinished
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

    async def seen(self, event: RunEvent) -> None:
        match event:
            case ReplyEnded(text=text, thoughts=thoughts):
                self.replies += 1
                if thoughts.strip():
                    await self.trace.add(E.THOUGHT, payload={"text": thoughts})
                if text.strip():
                    self.final_parts.append(text)
                    await self.trace.add(E.TEXT, payload={"text": text})
            case ToolCalled(call_id=call_id, tool=tool, input=arguments):
                self.calls[call_id] = tool
                self.final_parts = []
                await self.trace.add(E.TOOL_CALL, tool=tool, payload={"call_id": call_id, "arguments": dict(arguments)})
            case ToolFinished(call_id=call_id, text=text, is_error=is_error):
                await self.result(call_id, text, is_error)
            case _:
                return

    async def result(self, call_id: str, text: str, is_error: bool) -> None:
        tool = self.calls.pop(call_id, "")
        payload = {"call_id": call_id, "text": text, "is_error": is_error, "outcome": outcome_line(text, is_error)}
        await self.trace.add(E.TOOL_RESULT, tool=tool, payload=payload)
