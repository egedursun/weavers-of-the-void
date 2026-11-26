import asyncio
import json
from typing import Any

import httpx
import pytest
from openai import AsyncOpenAI

from aerona.llm.backends.base import RunRequest, StopReason
from aerona.llm.backends.openai import OpenAIBackend
from aerona.llm.content import probe_image
from aerona.llm.errors import LlmPermanentError, LlmTransientError, LlmUnavailableError
from aerona.llm.events import ReplyEnded, RunEvent, TextDelta, ToolPreparing
from aerona.llm.tools import AgentTool, ToolReply
from tests.providers.stand_in_model import StandInModel

SCHEMA = {"type": "object", "properties": {"name": {"type": "string"}}}


def backend(model: StandInModel, prefix: str = "openai/") -> OpenAIBackend:
    client = AsyncOpenAI(base_url="http://gateway.test/v1", api_key="sk-workspace", max_retries=0, http_client=httpx.AsyncClient(transport=model.transport()))
    return OpenAIBackend(client, prefix)


def star_tool(heard: list[dict[str, Any]]) -> AgentTool:
    async def handler(arguments: dict[str, Any]) -> ToolReply:
        heard.append(arguments)
        return ToolReply("Vela burns blue")

    return AgentTool("lookup_star", "Look up a star", SCHEMA, handler)


async def test_a_tool_round_streams_and_answers_through_the_model() -> None:
    model = StandInModel()
    heard: list[dict[str, Any]] = []
    events: list[RunEvent] = []
    end = await backend(model).run(RunRequest("Be brief.", "Find Vela.", (star_tool(heard),), "fast", 5), events.append, asyncio.Event())
    assert end.stop is StopReason.COMPLETED and end.turns == 2
    assert heard == [{"name": "Vela"}]
    assert ToolPreparing("call_a", "lookup_star") in events
    assert TextDelta("Found: Vela burns blue") in events
    assert [event.text for event in events if isinstance(event, ReplyEnded)] == ["", "Found: Vela burns blue"]
    first, second = model.requests
    assert first["model"] == "openai/fast" and first["messages"][0] == {"role": "system", "content": "Be brief."}
    assert second["messages"][-1] == {"role": "tool", "tool_call_id": "call_a", "content": "Vela burns blue"}


async def test_the_key_and_the_gateway_header_go_with_every_request() -> None:
    model = StandInModel()
    client = AsyncOpenAI(
        base_url="http://gateway.test/v1",
        api_key="sk-workspace",
        default_headers={"x-bf-direct-key": "true"},
        http_client=httpx.AsyncClient(transport=model.transport()),
    )
    await OpenAIBackend(client, "openai/").run(RunRequest("", "Hi.", (), "fast", 2), lambda event: None, asyncio.Event())
    assert model.headers[0]["authorization"] == "Bearer sk-workspace" and model.headers[0]["x-bf-direct-key"] == "true"


async def test_pictures_go_as_data_addresses_and_runs_stop_at_their_limit() -> None:
    model = StandInModel(
        reply=lambda body: {"tool_calls": [{"index": 0, "id": "c1", "type": "function", "function": {"name": "lookup_star", "arguments": "{}"}}]}
    )
    end = await backend(model).run(RunRequest("", "Look.", (star_tool([]),), "fast", 2, (probe_image(),)), lambda event: None, asyncio.Event())
    assert end.stop is StopReason.STEP_LIMIT and end.turns == 2
    content = model.requests[0]["messages"][1]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


async def test_broken_arguments_and_unknown_tools_answer_the_model_with_an_error() -> None:
    def reply(body: dict[str, Any]) -> dict[str, Any]:
        if any(message["role"] == "tool" for message in body["messages"]):
            return {"content": json.dumps([message["content"] for message in body["messages"] if message["role"] == "tool"])}
        calls = [
            {"index": 0, "id": "c1", "type": "function", "function": {"name": "lookup_star", "arguments": "{broken"}},
            {"index": 1, "id": "c2", "type": "function", "function": {"name": "nowhere", "arguments": "{}"}},
        ]
        return {"tool_calls": calls}

    events: list[RunEvent] = []
    await backend(StandInModel(reply=reply)).run(RunRequest("", "Go.", (star_tool([]),), "fast", 4), events.append, asyncio.Event())
    final = [event.text for event in events if isinstance(event, ReplyEnded)][-1]
    assert json.loads(final) == ["The arguments were not valid JSON.", "No tool is named nowhere."]


@pytest.mark.parametrize(("status", "error"), [(401, LlmUnavailableError), (429, LlmTransientError), (503, LlmTransientError), (400, LlmPermanentError)])
async def test_provider_answers_map_to_the_chain_errors(status: int, error: type[Exception]) -> None:
    with pytest.raises(error):
        await backend(StandInModel(status=status)).run(RunRequest("", "Hi.", (), "fast", 2), lambda event: None, asyncio.Event())


async def test_models_are_listed_without_the_gateway_prefix() -> None:
    assert await backend(StandInModel()).models() == ["a-model", "b-model"]


async def test_the_gateway_is_told_whose_models_a_direct_key_lists_and_a_local_server_is_not() -> None:
    gateway = StandInModel()
    await backend(gateway).models()
    local = StandInModel()
    await backend(local, "").models()
    assert gateway.addresses[-1].endswith("/models?provider=openai")
    assert local.addresses[-1].endswith("/models")
