import json
import secrets
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.db.tables.divine_will import DivineWillHandleRow
from aerona.domain.enums.divine_will import DivineWillMode
from aerona.llm.token_count import count_tokens
from aerona.llm.tools import AgentTool, ToolReply
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.rules.registry import Rules
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.schema import input_schema


class Toolset(StrEnum):
    READ = "read"
    ACT = "act"
    CATALOG_READ = "catalog_read"
    MECHANICS = "mechanics"
    RULES_READ = "rules_read"
    PLAN = "plan"
    FORESIGHT = "foresight"
    ARTIFACTS = "artifacts"
    ARTIFACTS_READ = "artifacts_read"
    ATTACHMENTS = "attachments"
    NOTICES = "notices"


T = Toolset
MODE_TOOLSETS: Mapping[DivineWillMode, frozenset[Toolset]] = {
    DivineWillMode.COMMAND: frozenset({T.READ, T.ACT, T.CATALOG_READ, T.RULES_READ, T.ARTIFACTS_READ, T.ATTACHMENTS, T.NOTICES}),
    DivineWillMode.PLAN: frozenset({T.READ, T.CATALOG_READ, T.RULES_READ, T.PLAN, T.FORESIGHT, T.ATTACHMENTS, T.NOTICES}),
    DivineWillMode.ASK_LORE: frozenset({T.READ, T.ARTIFACTS_READ, T.ATTACHMENTS, T.NOTICES}),
    DivineWillMode.CREATIVE_WORK: frozenset({T.READ, T.ARTIFACTS, T.ARTIFACTS_READ, T.ATTACHMENTS, T.NOTICES}),
    DivineWillMode.MECHANICS_GUIDE: frozenset({T.MECHANICS, T.CATALOG_READ, T.NOTICES}),
    DivineWillMode.FORESIGHT: frozenset({T.READ, T.CATALOG_READ, T.RULES_READ, T.FORESIGHT, T.ATTACHMENTS, T.NOTICES}),
}


class PagedInput(ToolInput):
    page: int = 1


@dataclass(frozen=True)
class WillResult:
    text: str
    is_error: bool = False
    handle: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)
    pause: bool = False


class PlayerPort(Protocol):
    async def preview(self, action_id: str, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...

    async def perform(self, action_id: str, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...

    async def undo(self, ledger_entry_id: int) -> Mapping[str, Any]: ...

    async def job(self, job_id: str) -> Mapping[str, Any]: ...


class WillCall:
    def __init__(
        self,
        database: Database,
        rules: Rules,
        *,
        cycle_id: int,
        session_id: int,
        epoch: int,
        mode: DivineWillMode,
        lore_language: str,
        player: PlayerPort,
        services: Any,
    ) -> None:
        self.database = database
        self.rules = rules
        self.cycle_id = cycle_id
        self.session_id = session_id
        self.epoch = epoch
        self.mode = mode
        self.lore_language = lore_language
        self.player = player
        self.services = services

    async def remember(self, session: AsyncSession, tool: DivineWillToolId, query: Mapping[str, Any], total: int) -> str:
        key = secrets.token_urlsafe(9)
        session.add(DivineWillHandleRow(key=key, cycle_id=self.cycle_id, tool=tool.value, query=dict(query), total=total))
        await session.flush()
        return key


@dataclass(frozen=True)
class WillTool[InputT: ToolInput]:
    tool_id: DivineWillToolId
    toolsets: frozenset[Toolset]
    input_model: type[InputT]
    handler: Callable[[WillCall, InputT], Awaitable[WillResult]]

    @property
    def name(self) -> str:
        return self.tool_id.value


@dataclass(frozen=True)
class Page[ItemT]:
    items: Sequence[ItemT]
    total: int
    page: int
    has_next: bool


def page_items[ItemT](items: Sequence[ItemT], render: Callable[[ItemT], str], budget: int, page: int) -> tuple[Page[ItemT], str]:
    pages: list[tuple[int, int]] = []
    start = 0
    while start < len(items):
        used = 0
        end = start
        while end < len(items):
            cost = count_tokens(render(items[end]))
            if end > start and used + cost > budget:
                break
            used += cost
            end += 1
        pages.append((start, end))
        start = end
    if not pages:
        return Page([], 0, 1, False), ""
    index = min(max(1, page), len(pages)) - 1
    low, high = pages[index]
    chosen = items[low:high]
    return Page(chosen, len(items), index + 1, index + 1 < len(pages)), "\n".join(render(item) for item in chosen)


def page_text(text: str, budget: int, page: int) -> tuple[str, int, bool]:
    blocks = text.split("\n\n")
    page_info, body = page_items(blocks, lambda block: block + "\n", budget, page)
    return body, page_info.page, page_info.has_next


def envelope(text: str, *, total: int, shown: int, page: int, has_next: bool, handle: str) -> str:
    head = {"total": total, "shown": shown, "page": page, "next": has_next, "handle": handle}
    return f"{json.dumps(head)}\n{text}" if text else json.dumps(head)


def will_agent_tool(
    call: WillCall, tool: WillTool[Any], description: str, fields: Mapping[str, str], run: Callable[[WillTool[Any], dict[str, Any]], Awaitable[WillResult]]
) -> AgentTool:
    async def handler(arguments: dict[str, Any]) -> ToolReply:
        result = await run(tool, dict(arguments or {}))
        return ToolReply(result.text, result.is_error)

    return AgentTool(name=tool.name, description=description, input_schema=input_schema(tool.input_model, fields), handler=handler)


async def invoke(call: WillCall, tool: WillTool[Any], arguments: Mapping[str, Any]) -> WillResult:
    try:
        parsed = tool.input_model.model_validate(dict(arguments))
    except ValidationError as error:
        return WillResult(text=f"The input did not fit {tool.name}: {error.errors(include_url=False)}", is_error=True)
    return await tool.handler(call, parsed)
