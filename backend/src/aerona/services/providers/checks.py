import asyncio
from datetime import datetime

from aerona.catalog.providers import (
    CHECK_DRAWING_PROMPT,
    CHECK_PICTURE_ANSWER,
    CHECK_PICTURE_PROMPT,
    CHECK_PROMPT,
    CHECK_SYSTEM,
    CHECK_TOOL,
    CHECK_TOOL_DESCRIPTION,
    CHECK_WORD,
    IMAGE_MODEL_MARKS,
)
from aerona.constants.providers import (
    CHECK_DRAWING_SEED,
    CHECK_DRAWING_SIDE,
    CHECK_DRAWING_STEPS,
    CHECK_NOTE_MAX_LENGTH,
    CHECK_SECONDS,
    CHECK_TURNS,
)
from aerona.domain.enums.providers import ModelRole
from aerona.imaging.client import ImageWorkerClient
from aerona.imaging.contract import ImageJobRequest, ImagePriority
from aerona.imaging.errors import ImageWorkerError
from aerona.imaging.provider import ImageProvider
from aerona.llm.backends.base import ModelBackend, RunRequest
from aerona.llm.content import probe_image
from aerona.llm.errors import LlmError
from aerona.llm.events import ReplyEnded, RunEvent
from aerona.llm.tools import AgentTool, ToolReply
from aerona.services.providers.store import CheckResult

ECHO_SCHEMA = {"type": "object", "properties": {"word": {"type": "string"}}, "required": ["word"]}
TOOL_UNUSED = "The model did not call the test tool."
PICTURE_UNSEEN = "The model did not see the test picture."
WORKER_DOWN = "The image worker did not answer: {reason}"
DRAWING_FAILED = "It did not draw the test picture: {reason}"


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


def picture_model(name: str) -> bool:
    lowered = name.lower()
    return any(mark in lowered for mark in IMAGE_MODEL_MARKS)


def failure_note(template: str, error: BaseException) -> str:
    return template.format(reason=str(error) or type(error).__name__)[:CHECK_NOTE_MAX_LENGTH]


async def check_worker(worker: ImageWorkerClient, now: datetime) -> CheckResult:
    try:
        health = await asyncio.wait_for(worker.health(), CHECK_SECONDS)
    except (ImageWorkerError, LlmError, TimeoutError) as error:
        return CheckResult(False, None, failure_note(WORKER_DOWN, error), now)
    return CheckResult(True, None, f"{health.backend} · {health.model_id}"[:CHECK_NOTE_MAX_LENGTH], now)


async def check_drawing(provider: ImageProvider, now: datetime) -> CheckResult:
    job = ImageJobRequest(
        prompt=CHECK_DRAWING_PROMPT,
        width=CHECK_DRAWING_SIDE,
        height=CHECK_DRAWING_SIDE,
        steps=CHECK_DRAWING_STEPS,
        seed=CHECK_DRAWING_SEED,
        priority=ImagePriority.MANUAL,
    )
    try:
        await asyncio.wait_for(provider.generate(job), CHECK_SECONDS)
    except (ImageWorkerError, LlmError, TimeoutError) as error:
        return CheckResult(False, None, failure_note(DRAWING_FAILED, error), now)
    return CheckResult(True, None, "", now)
