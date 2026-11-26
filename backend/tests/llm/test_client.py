import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from aerona.api.schemas.events import RetryPayload
from aerona.catalog.providers import ANSWER_INSTRUCTION, ANSWER_RECORDED, ANSWER_TOOL
from aerona.constants.llm import RETRY_KIND
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.providers import ModelRole
from aerona.events.kinds import EventKind
from aerona.llm.backends.base import StopReason
from aerona.llm.client import LlmClient
from aerona.llm.content import ImagePart, probe_image
from aerona.llm.errors import LlmDisabledError, LlmPermanentError, LlmTimeoutError, LlmTransientError, LlmUnavailableError
from aerona.llm.events import RunEvent
from aerona.llm.records import CallOutcome, CallRecord, Usage
from aerona.llm.stream import StreamActor, current_actor
from aerona.llm.token_count import TokenMeter, tool_text
from aerona.llm.tools import AgentTool, ToolReply
from tests.llm.fakes import Call, FakeBackend, FakeRoutes, FixedRules, Hang, Speak, answered, as_json, every_role, route


class Verdict(BaseModel):
    accepted: bool
    reason: str


FITS = {"accepted": True, "reason": "fits"}


def client(routes: FakeRoutes, records: list[CallRecord] | None = None, events: list[tuple[EventKind, dict[str, Any]]] | None = None) -> LlmClient:
    async def sink(record: CallRecord) -> None:
        if records is not None:
            records.append(record)

    def publish(kind: EventKind, payload: dict[str, Any]) -> None:
        if events is not None:
            events.append((kind, payload))

    return LlmClient(FixedRules(), enabled=True, routes=routes, metrics=sink, publish=publish)


def looking() -> AgentTool:
    async def handler(arguments: dict[str, Any]) -> ToolReply:
        del arguments
        return ToolReply("hello world")

    return AgentTool("look", "Look around.", {"type": "object", "properties": {}}, handler)


async def test_a_structured_call_takes_the_answer_tool_and_names_the_model() -> None:
    records: list[CallRecord] = []
    backend = FakeBackend([answered(FITS)])
    verdict = await client(every_role(route(backend)), records).structured("fate", "system", "prompt", output=Verdict)
    assert verdict == Verdict(accepted=True, reason="fits")
    request = backend.requests[0]
    assert request.model == "fake-model"
    assert [tool.name for tool in request.tools] == [ANSWER_TOOL]
    assert request.system.endswith(ANSWER_INSTRUCTION)
    assert backend.replies == [ANSWER_RECORDED]
    assert records[0].outcome is CallOutcome.OK
    assert records[0].model == "fake-model · Test"
    assert not hasattr(Usage(), "cost_usd")


async def test_an_answer_that_does_not_fit_is_sent_back_within_the_same_run() -> None:
    backend = FakeBackend([[Call(ANSWER_TOOL, {"wrong": 1}), Call(ANSWER_TOOL, FITS)]])
    verdict = await client(every_role(route(backend))).structured("fate", "system", "prompt", output=Verdict)
    assert verdict.accepted is True
    assert len(backend.requests) == 1
    assert backend.replies[0].startswith("The result does not fit")
    assert backend.replies[1] == ANSWER_RECORDED


async def test_a_result_written_as_text_is_taken_when_no_answer_was_called() -> None:
    backend = FakeBackend([[Speak(f"Here it is: {as_json(FITS)}")]])
    verdict = await client(every_role(route(backend))).structured("fate", "system", "prompt", output=Verdict)
    assert verdict.reason == "fits"


async def test_a_run_without_a_result_is_retried() -> None:
    backend = FakeBackend([[Speak("no idea")], answered(FITS)])
    events: list[tuple[EventKind, dict[str, Any]]] = []
    verdict = await client(every_role(route(backend)), events=events).structured("fate", "system", "prompt", output=Verdict)
    assert verdict.accepted is True
    assert len(backend.requests) == 2
    retries = [payload for kind, payload in events if kind is EventKind.AGENT_RETRY]
    assert len(retries) == 1
    assert retries[0]["actor"] == "fate"
    assert retries[0]["kind"] == RETRY_KIND
    assert (retries[0]["attempt"], retries[0]["total"]) == (2, 3)
    assert (retries[0]["wait_s"], retries[0]["kept_steps"]) == (0, 0)
    assert RetryPayload.model_validate(retries[0]).wait_s == 0


async def test_an_unreachable_model_hands_the_call_to_the_next_in_the_chain() -> None:
    records: list[CallRecord] = []
    broken = FakeBackend([[LlmUnavailableError("not logged in")]])
    working = FakeBackend([answered(FITS)])
    routes = every_role(route(broken, "First"), route(working, "Second"))
    verdict = await client(routes, records).structured("fate", "system", "prompt", output=Verdict)
    assert verdict.accepted is True
    assert len(broken.requests) == 1
    assert [(record.model, record.outcome) for record in records] == [("fake-model · First", CallOutcome.FAILED), ("fake-model · Second", CallOutcome.OK)]


async def test_a_model_that_keeps_failing_hands_over_after_its_retries() -> None:
    failing = FakeBackend([[LlmTransientError("busy")] for _ in range(3)])
    working = FakeBackend([answered(FITS)])
    verdict = await client(every_role(route(failing, "First"), route(working, "Second"))).structured("fate", "system", "prompt", output=Verdict)
    assert verdict.accepted is True
    assert len(failing.requests) == 3


async def test_a_permanent_error_is_not_retried_and_the_last_failure_is_raised() -> None:
    backend = FakeBackend([[LlmPermanentError("bad request")]])
    with pytest.raises(LlmPermanentError):
        await client(every_role(route(backend))).structured("fate", "system", "prompt", output=Verdict)
    assert len(backend.requests) == 1


async def test_a_hung_model_times_out() -> None:
    backend = FakeBackend([[Hang()]])
    with pytest.raises(LlmTimeoutError):
        await client(every_role(route(backend))).structured("fate", "system", "prompt", output=Verdict, attempts=1, timeout_seconds=1)


async def test_a_role_with_no_model_never_calls_one() -> None:
    records: list[CallRecord] = []
    backend = FakeBackend()
    routes = FakeRoutes({ModelRole.WORLD_AGENTS: [route(backend)]})
    model = client(routes, records)
    with pytest.raises(LlmDisabledError):
        await model.structured("fate", "system", "prompt", output=Verdict)
    assert backend.requests == []
    assert records[0].outcome is CallOutcome.DISABLED
    assert model.ready(ModelRole.WORLD_AGENTS) and not model.ready(ModelRole.WRITING)
    assert model.model_of(ModelRole.WORLD_AGENTS) == "fake-model · Test"
    assert model.model_of(ModelRole.WRITING) == ""


async def test_a_disabled_client_is_off_whatever_its_chains() -> None:
    model = LlmClient(FixedRules(), enabled=False, routes=every_role(route(FakeBackend())))
    assert not model.enabled
    assert not model.ready(ModelRole.WRITING)
    with pytest.raises(LlmDisabledError):
        await model.structured("fate", "system", "prompt", output=Verdict)


async def test_an_agent_run_counts_every_reply_and_tool_result() -> None:
    records: list[CallRecord] = []
    tool = looking()
    backend = FakeBackend([[Call("look"), Speak("done")]])
    run = await client(every_role(route(backend)), records).run_agent("Son turn: Ithren", "system", "prompt", tools=[tool])
    assert run.completed and run.stop_reason == StopReason.COMPLETED.value
    assert run.text == "done"
    expected = TokenMeter("system", tool_text(tool), "prompt")
    expected.reply("")
    expected.produced("look\n{}")
    expected.returned("hello world")
    expected.reply("done")
    assert (records[0].usage.input_tokens, records[0].usage.output_tokens) == (expected.input_tokens, expected.output_tokens)
    assert records[0].usage.turns == 2


async def test_a_tool_call_keeps_the_id_it_was_prepared_with() -> None:
    events: list[tuple[EventKind, dict[str, Any]]] = []
    backend = FakeBackend([[Call("look"), Speak("done")]])
    token = current_actor.set(StreamActor(ActorKind.SON, 3, "Ithren"))
    try:
        await client(every_role(route(backend)), events=events).run_agent("Son turn: Ithren", "system", "prompt", tools=[looking()])
    finally:
        current_actor.reset(token)
    ids = {
        kind: payload["call_id"]
        for kind, payload in events
        if kind in {EventKind.AGENT_TOOL_PREPARING, EventKind.AGENT_TOOL_CALLED, EventKind.AGENT_TOOL_RESULT}
    }
    assert ids == {EventKind.AGENT_TOOL_PREPARING: "p0", EventKind.AGENT_TOOL_CALLED: "p0", EventKind.AGENT_TOOL_RESULT: "p0"}


class StoppingWatch:
    def __init__(self) -> None:
        self.events: list[RunEvent] = []

    @property
    def stopped(self) -> bool:
        return len(self.events) >= 2

    async def seen(self, event: RunEvent) -> None:
        self.events.append(event)


async def test_a_watch_that_stops_ends_the_run() -> None:
    watch = StoppingWatch()
    backend = FakeBackend([[Call("look"), Speak("never said")]])
    run = await client(every_role(route(backend))).run_agent("divine_will", "system", "prompt", tools=[looking()], watch=watch)
    assert not run.completed
    assert run.stop_reason == StopReason.STOPPED.value
    assert "never said" not in run.text


async def test_pictures_reach_only_a_model_that_sees_them() -> None:
    picture = probe_image()
    seeing = FakeBackend()
    await client(every_role(route(seeing))).run_agent("will", "system", "Look.", tools=[], images=[picture], role=ModelRole.CONVERSATION)
    assert seeing.requests[0].images == (picture,)
    blind = FakeBackend()
    blind_route = route(blind, sees_images=False)
    await client(every_role(blind_route)).run_agent("will", "system", "Look.", tools=[], images=[ImagePart("image/png", b"x")], role=ModelRole.CONVERSATION)
    assert blind.requests[0].images == ()


async def test_capabilities_come_from_the_check_of_the_first_model() -> None:
    seen = await client(every_role(route(FakeBackend(), sees_images=True))).capabilities()
    assert seen.images and seen.probed
    unchecked = await client(every_role(route(FakeBackend(), sees_images=None))).capabilities()
    assert not unchecked.images and not unchecked.probed and unchecked.note
    blind = await client(every_role(route(FakeBackend(), sees_images=False))).capabilities()
    assert not blind.images and blind.probed and blind.note
    nothing = await client(FakeRoutes()).capabilities()
    assert not nothing.images and not nothing.probed


LEGACY_VOCABULARY = Path("aerona/migration/legacy/schema_map.json")


def test_no_source_file_names_a_model_family() -> None:
    source_root = Path(__file__).resolve().parents[2] / "src"
    offenders = [
        path
        for path in source_root.rglob("*")
        if path.is_file()
        and path.relative_to(source_root) != LEGACY_VOCABULARY
        and path.suffix in {".py", ".j2", ".json", ".yaml"}
        and re.search(r"\b(?:sonnet|opus)\b", path.read_text(encoding="utf-8"), re.IGNORECASE)
    ]
    assert offenders == []
