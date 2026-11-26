from typing import Any

from pydantic import BaseModel

from aerona.catalog.providers import ANSWER_TOOL
from aerona.domain.enums.node import ActorKind
from aerona.events.kinds import EventKind
from aerona.llm.client import LlmClient
from aerona.llm.events import ReplyEnded, TextDelta, ToolCalled, ToolFinished, ToolPreparing, ToolWriting
from aerona.llm.stream import StreamActor, StreamReporter, current_actor
from aerona.llm.tools import AgentTool, ToolReply
from aerona.rules.registry import Rules
from aerona.rules.registry.model import ModelRules
from aerona.rules.registry.server import ServerRules
from tests.llm.fakes import Call, FakeBackend, Speak, every_role, route

ACTOR = StreamActor(ActorKind.SON, 7, "Velkar", frozenset({"look_around"}))


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Verdict(BaseModel):
    accepted: bool


class ServerOnly:
    def __init__(self, server: ServerRules) -> None:
        self.current = Rules(model=ModelRules(retry_wait_1=0, retry_wait_2=0, retry_wait_3=0), server=server)


def collector() -> tuple[list[tuple[EventKind, dict[str, Any]]], Any]:
    seen: list[tuple[EventKind, dict[str, Any]]] = []

    def publish(kind: EventKind, payload: dict[str, Any]) -> None:
        seen.append((kind, payload))

    return seen, publish


def kinds(seen: list[tuple[EventKind, dict[str, Any]]]) -> list[EventKind]:
    return [kind for kind, _ in seen]


def test_streamed_text_is_batched_by_the_emit_interval() -> None:
    seen, publish = collector()
    clock = Clock()
    reporter = StreamReporter(publish, ServerRules(stream_emit_interval_ms=150), ACTOR, "turn", clock)
    for index, piece in enumerate(["The ", "tide ", "turns", " slow"]):
        clock.now = index * 0.05
        reporter.feed(TextDelta(piece))
    reporter.close()
    assert [payload["text"] for _, payload in seen] == ["The ", "tide turns slow"]
    assert seen[0][1] == {"actor_kind": "son", "actor_id": 7, "actor_name": "Velkar", "text": "The ", "chars": 4}
    assert seen[1][1]["chars"] == 4 + len("tide turns slow")


def test_tool_lifecycle_emits_preparing_writing_called_and_result() -> None:
    seen, publish = collector()
    reporter = StreamReporter(publish, ServerRules(tool_write_step_chars=10), ACTOR, "turn", Clock())
    reporter.feed(ToolPreparing("toolu_1", "look_around"))
    reporter.feed(ToolWriting("toolu_1", "look_around", len('{"where":')))
    reporter.feed(ToolWriting("toolu_1", "look_around", len('{"where":"north"}')))
    reporter.feed(ToolCalled("toolu_1", "look_around", {"where": "north"}))
    reporter.feed(ToolFinished("toolu_1", "look_around", "x" * 500, False))
    assert kinds(seen) == [
        EventKind.AGENT_TOOL_PREPARING,
        EventKind.AGENT_TOOL_WRITING,
        EventKind.AGENT_TOOL_CALLED,
        EventKind.AGENT_TOOL_RESULT,
    ]
    assert seen[0][1]["tool"] == "look_around" and seen[0][1]["call_id"] == "toolu_1"
    assert seen[1][1]["chars"] == len('{"where":"north"}')
    assert seen[2][1]["input"] == {"where": "north"} and seen[2][1]["read_only"] is True
    result = seen[3][1]
    assert len(result["text"]) == 400 and result["error"] is False and result["quiet"] is True and result["tool"] == "look_around"


def test_write_tool_results_are_not_quiet_and_errors_are_flagged() -> None:
    seen, publish = collector()
    reporter = StreamReporter(publish, ServerRules(), ACTOR, "turn", Clock())
    reporter.feed(ToolCalled("t2", "create_entity", {}))
    reporter.feed(ToolFinished("t2", "create_entity", "REFUSED: no actions left", True))
    assert seen[0][1]["read_only"] is False
    assert seen[1][1] == {**seen[1][1], "error": True, "quiet": False, "text": "REFUSED: no actions left"}


def test_a_finished_reply_emits_its_text_as_a_thought() -> None:
    seen, publish = collector()
    reporter = StreamReporter(publish, ServerRules(), ACTOR, "turn", Clock())
    reporter.feed(ReplyEnded("I will build a wall.", ""))
    reporter.feed(ReplyEnded("  ", "only thinking"))
    assert kinds(seen) == [EventKind.AGENT_THOUGHT]
    assert seen[0][1]["text"] == "I will build a wall."


def test_long_structured_writes_report_progress_on_the_writing_interval() -> None:
    seen, publish = collector()
    clock = Clock()
    reporter = StreamReporter(publish, ServerRules(writing_emit_interval_ms=1000), None, "fate:judgement", clock)
    reporter.feed(ToolPreparing("s", ANSWER_TOOL))
    for number, second in enumerate((0.0, 0.4, 0.8, 1.2, 1.5), start=1):
        clock.now = second
        reporter.feed(ToolWriting("s", ANSWER_TOOL, 5 * number))
    reporter.close()
    assert kinds(seen) == [EventKind.AGENT_WRITING] * 3
    assert [payload["chars"] for _, payload in seen] == [5, 20, 25]
    assert [payload["finished"] for _, payload in seen] == [False, False, True]
    assert seen[-1][1]["status"] == "ok" and seen[-1][1]["who"] == "fate:judgement"
    assert len({payload["stream_id"] for _, payload in seen}) == 1


def test_a_failed_write_closes_with_the_error() -> None:
    seen, publish = collector()
    reporter = StreamReporter(publish, ServerRules(), None, "chronicler", Clock())
    reporter.feed(TextDelta("partial"))
    reporter.close("timed out")
    assert seen[-1][1]["finished"] is True and seen[-1][1]["status"] == "error" and seen[-1][1]["error"] == "timed out"


async def test_client_streams_structured_progress_through_its_publisher() -> None:
    seen, publish = collector()
    backend = FakeBackend([[Speak("weighing"), Call(ANSWER_TOOL, {"accepted": True})]])
    client = LlmClient(ServerOnly(ServerRules(writing_emit_interval_ms=50)), enabled=True, routes=every_role(route(backend)), publish=publish)
    verdict = await client.structured("epic", "system", "prompt", output=Verdict)
    assert verdict.accepted is True
    assert kinds(seen) == [EventKind.AGENT_WRITING, EventKind.AGENT_WRITING]
    assert seen[-1][1]["finished"] is True and seen[-1][1]["status"] == "ok" and seen[-1][1]["who"] == "epic"


async def test_client_streams_agent_events_for_the_current_actor() -> None:
    seen, publish = collector()

    async def look(arguments: dict[str, Any]) -> ToolReply:
        del arguments
        return ToolReply("nothing stirs")

    backend = FakeBackend([[Speak("Thinking."), Call("look_around")]])
    client = LlmClient(ServerOnly(ServerRules()), enabled=True, routes=every_role(route(backend)), publish=publish)
    token = current_actor.set(ACTOR)
    try:
        run = await client.run_agent("turn", "system", "prompt", tools=[AgentTool("look_around", "Look.", {"type": "object"}, look)])
    finally:
        current_actor.reset(token)
    assert run.completed
    assert kinds(seen) == [
        EventKind.AGENT_STREAM,
        EventKind.AGENT_THOUGHT,
        EventKind.AGENT_TOOL_PREPARING,
        EventKind.AGENT_TOOL_CALLED,
        EventKind.AGENT_TOOL_RESULT,
    ]
    assert all(payload["actor_id"] == 7 for _, payload in seen)
