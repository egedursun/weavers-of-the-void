import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from claude_agent_sdk import ResultMessage
from pydantic import BaseModel

from aerona.api.schemas.events import RetryPayload
from aerona.constants.llm import HAIKU_MODEL_ID, RETRY_KIND
from aerona.events.kinds import EventKind
from aerona.llm.client import LlmClient
from aerona.llm.errors import LlmDisabledError, LlmPermanentError
from aerona.llm.records import CallOutcome, CallRecord
from aerona.rules.registry import Rules
from aerona.rules.registry.model import ModelRules


class Verdict(BaseModel):
    accepted: bool
    reason: str


class FixedRules:
    def __init__(self) -> None:
        self.current = Rules(model=ModelRules(retry_wait_1=0, retry_wait_2=0, retry_wait_3=0))


def result(**overrides: Any) -> ResultMessage:
    values: dict[str, Any] = {
        "subtype": "success",
        "duration_ms": 1,
        "duration_api_ms": 1,
        "is_error": False,
        "num_turns": 1,
        "session_id": "s",
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "total_cost_usd": 0.001,
        "result": None,
        "structured_output": {"accepted": True, "reason": "fits"},
    }
    values.update(overrides)
    return ResultMessage(**values)


def scripted(*responses: ResultMessage | Exception) -> tuple[Any, list[Any]]:
    calls: list[Any] = []
    queue = list(responses)

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        calls.append(options)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        yield item

    return fake_query, calls


async def test_structured_call_uses_haiku_and_parses_output() -> None:
    records: list[CallRecord] = []

    async def sink(record: CallRecord) -> None:
        records.append(record)

    fake_query, calls = scripted(result())
    client = LlmClient(FixedRules(), enabled=True, metrics=sink, query_function=fake_query)
    verdict = await client.structured("fate", "system", "prompt", output=Verdict)
    assert verdict == Verdict(accepted=True, reason="fits")
    assert calls[0].model == HAIKU_MODEL_ID
    assert calls[0].fallback_model is None
    assert calls[0].tools == []
    assert records[0].outcome == CallOutcome.OK
    assert records[0].usage.input_tokens == 10


async def test_transient_failure_is_retried_then_succeeds() -> None:
    fake_query, calls = scripted(result(is_error=True, api_error_status=529, structured_output=None), result())
    client = LlmClient(FixedRules(), enabled=True, query_function=fake_query)
    verdict = await client.structured("fate", "system", "prompt", output=Verdict)
    assert verdict.accepted is True
    assert len(calls) == 2


async def test_retry_is_announced_with_its_wait() -> None:
    events: list[tuple[EventKind, dict[str, Any]]] = []
    fake_query, _ = scripted(result(is_error=True, api_error_status=529, structured_output=None), result())
    client = LlmClient(FixedRules(), enabled=True, query_function=fake_query, publish=lambda kind, payload: events.append((kind, payload)))
    await client.structured("fate", "system", "prompt", output=Verdict)
    retries = [payload for kind, payload in events if kind is EventKind.AGENT_RETRY]
    assert len(retries) == 1
    assert retries[0]["actor"] == "fate"
    assert retries[0]["kind"] == RETRY_KIND
    assert (retries[0]["attempt"], retries[0]["total"]) == (2, 3)
    assert (retries[0]["wait_s"], retries[0]["kept_steps"]) == (0, 0)
    assert RetryPayload.model_validate(retries[0]).wait_s == 0


async def test_schema_mismatch_is_retried() -> None:
    fake_query, calls = scripted(result(structured_output={"wrong": 1}), result())
    client = LlmClient(FixedRules(), enabled=True, query_function=fake_query)
    await client.structured("fate", "system", "prompt", output=Verdict)
    assert len(calls) == 2


async def test_permanent_error_is_not_retried() -> None:
    fake_query, calls = scripted(result(is_error=True, api_error_status=400, structured_output=None))
    client = LlmClient(FixedRules(), enabled=True, query_function=fake_query)
    with pytest.raises(LlmPermanentError):
        await client.structured("fate", "system", "prompt", output=Verdict)
    assert len(calls) == 1


async def test_disabled_client_never_calls_the_model() -> None:
    fake_query, calls = scripted()
    client = LlmClient(FixedRules(), enabled=False, query_function=fake_query)
    with pytest.raises(LlmDisabledError):
        await client.structured("fate", "system", "prompt", output=Verdict)
    assert calls == []


def test_only_haiku_is_ever_configured() -> None:
    assert "haiku" in HAIKU_MODEL_ID
    assert "sonnet" not in HAIKU_MODEL_ID
    assert "opus" not in HAIKU_MODEL_ID


LEGACY_VOCABULARY = Path("aerona/migration/legacy/schema_map.json")


def test_no_source_file_mentions_another_model_family() -> None:
    source_root = Path(__file__).resolve().parents[2] / "src"
    offenders = [
        path
        for path in source_root.rglob("*")
        if path.is_file()
        and path.relative_to(source_root) != LEGACY_VOCABULARY
        and path.suffix in {".py", ".j2", ".json", ".yaml"}
        and re.search(r"sonnet|opus", path.read_text(encoding="utf-8"), re.IGNORECASE)
    ]
    assert offenders == []
