from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolReply:
    text: str
    is_error: bool = False


ToolHandler = Callable[[dict[str, Any]], Awaitable[ToolReply]]


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler
