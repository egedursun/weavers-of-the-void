import asyncio
from datetime import datetime

from aerona.catalog.providers import (
    CHECK_PICTURE_ANSWER,
    CHECK_PICTURE_PROMPT,
    CHECK_PROMPT,
    CHECK_SYSTEM,
    CHECK_TOOL,
    CHECK_TOOL_DESCRIPTION,
    CHECK_WORD,
)
from aerona.constants.providers import CHECK_NOTE_MAX_LENGTH, CHECK_SECONDS, CHECK_TURNS
from aerona.domain.enums.providers import ModelRole
from aerona.llm.backends.base import ModelBackend, RunRequest
from aerona.llm.content import probe_image
from aerona.llm.errors import LlmError
from aerona.llm.events import ReplyEnded, RunEvent
from aerona.llm.tools import AgentTool, ToolReply
from aerona.services.providers.store import CheckResult

ECHO_SCHEMA = {"type": "object", "properties": {"word": {"type": "string"}}, "required": ["word"]}
TOOL_UNUSED = "The model did not call the test tool."
PICTURE_UNSEEN = "The model did not see the test picture."


async def echo_works(backend: ModelBackend, model: str) -> bool:
    heard: list[str] = []

    async def echo(arguments: dict[str, object]) -> ToolReply:
        heard.append(str(arguments.get("word", "")))
        return ToolReply(str(arguments.get("word", "")))

    tool = AgentTool(CHECK_TOOL, CHECK_TOOL_DESCRIPTION, ECHO_SCHEMA, echo)
    await asyncio.wait_for(backend.run(RunRequest(CHECK_SYSTEM, CHECK_PROMPT, (tool,), model, CHECK_TURNS), ignore, asyncio.Event()), CHECK_SECONDS)
    return any(CHECK_WORD in word.lower() for word in heard)


async def sees_picture(backend: ModelBackend, model: str) -> bool:
    texts: list[str] = []

    def read(event: RunEvent) -> None:
        if isinstance(event, ReplyEnded):
            texts.append(event.text)

    request = RunRequest(CHECK_SYSTEM, CHECK_PICTURE_PROMPT, (), model, CHECK_TURNS, (probe_image(),))
    await asyncio.wait_for(backend.run(request, read, asyncio.Event()), CHECK_SECONDS)
    return CHECK_PICTURE_ANSWER in " ".join(texts).lower()


def ignore(event: RunEvent) -> None:
    del event


async def check_model(backend: ModelBackend, model: str, role: ModelRole, now: datetime) -> CheckResult:
    try:
        tools = await echo_works(backend, model)
        sees = await sees_picture(backend, model) if role is ModelRole.CONVERSATION and tools else None
    except (LlmError, TimeoutError) as error:
        return CheckResult(False, None, (str(error) or type(error).__name__)[:CHECK_NOTE_MAX_LENGTH], now)
    notes = [note for note, failed in ((TOOL_UNUSED, not tools), (PICTURE_UNSEEN, sees is False)) if failed]
    return CheckResult(tools, sees, " ".join(notes), now)
