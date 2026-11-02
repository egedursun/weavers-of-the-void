from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import AssistantMessage, ResultMessage, StreamEvent, TextBlock, ToolResultBlock, ToolUseBlock, UserMessage
from pydantic import BaseModel

from aerona.domain.enums.node import ActorKind
from aerona.events.kinds import EventKind
from aerona.llm.client import LlmClient
from aerona.llm.stream import StreamActor, StreamReporter, current_actor
from aerona.rules.registry import Rules
from aerona.rules.registry.model import ModelRules
from aerona.rules.registry.server import ServerRules

ACTOR = StreamActor(ActorKind.SON, 7, "Velkar", frozenset({"look_around"}))


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Verdict(BaseModel):
    accepted: bool


class FixedRules:
    def __init__(self, server: ServerRules) -> None:
        self.current = Rules(model=ModelRules(retry_wait_1=0, retry_wait_2=0, retry_wait_3=0), server=server)


def partial(event: dict[str, Any]) -> StreamEvent:
    return StreamEvent(uuid="u", session_id="s", event=event)


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
    reporter.feed(partial({"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}))
    for index, piece in enumerate(["The ", "salt ", "sleeps", " deep"]):
        clock.now = index * 0.05
        reporter.feed(partial({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": piece}}))
    reporter.feed(partial({"type": "content_block_stop", "index": 0}))
    assert [payload["text"] for _, payload in seen] == ["The ", "salt sleeps deep"]
    assert seen[0][1] == {"actor_kind": "son", "actor_id": 7, "actor_name": "Velkar", "text": "The ", "chars": 4}
    assert seen[1][1]["chars"] == 4 + len("salt sleeps deep")


def test_tool_lifecycle_emits_preparing_writing_called_and_result() -> None:
    seen, publish = collector()
    reporter = StreamReporter(publish, ServerRules(tool_write_step_chars=10), ACTOR, "turn", Clock())
    reporter.feed(
        partial({"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_1", "name": "mcp__aerona__look_around"}})
    )
    reporter.feed(partial({"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"where":'}}))
    reporter.feed(partial({"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '"north"}'}}))
    reporter.feed(partial({"type": "content_block_stop", "index": 1}))
    reporter.feed(AssistantMessage(content=[ToolUseBlock(id="toolu_1", name="mcp__aerona__look_around", input={"where": "north"})], model="m"))
    reporter.feed(UserMessage(content=[ToolResultBlock(tool_use_id="toolu_1", content=[{"type": "text", "text": "x" * 500}], is_error=False)]))
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
    reporter.feed(AssistantMessage(content=[ToolUseBlock(id="t2", name="mcp__aerona__create_entity", input={})], model="m"))
    reporter.feed(UserMessage(content=[ToolResultBlock(tool_use_id="t2", content="REFUSED: no actions left", is_error=True)]))
    assert seen[0][1]["read_only"] is False
    assert seen[1][1] == {**seen[1][1], "error": True, "quiet": False, "text": "REFUSED: no actions left"}


def test_thought_blocks_emit_the_final_text() -> None:
    seen, publish = collector()
    reporter = StreamReporter(publish, ServerRules(), ACTOR, "turn", Clock())
    reporter.feed(AssistantMessage(content=[TextBlock(text="I will build a wall."), TextBlock(text="  ")], model="m"))
    assert kinds(seen) == [EventKind.AGENT_THOUGHT]
    assert seen[0][1]["text"] == "I will build a wall."


def test_long_structured_writes_report_progress_on_the_writing_interval() -> None:
    seen, publish = collector()
    clock = Clock()
    reporter = StreamReporter(publish, ServerRules(writing_emit_interval_ms=1000), None, "fate:judgement", clock)
    reporter.feed(partial({"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "s", "name": "StructuredOutput"}}))
    for second in (0.0, 0.4, 0.8, 1.2, 1.5):
        clock.now = second
        reporter.feed(partial({"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "abcde"}}))
    reporter.close()
    assert kinds(seen) == [EventKind.AGENT_WRITING] * 3
    assert [payload["chars"] for _, payload in seen] == [5, 20, 25]
    assert [payload["finished"] for _, payload in seen] == [False, False, True]
    assert seen[-1][1]["status"] == "ok" and seen[-1][1]["who"] == "fate:judgement"
    assert len({payload["stream_id"] for _, payload in seen}) == 1


def test_a_failed_write_closes_with_the_error() -> None:
    seen, publish = collector()
    reporter = StreamReporter(publish, ServerRules(), None, "chronicler", Clock())
    reporter.feed(partial({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "partial"}}))
    reporter.close("timed out")
    assert seen[-1][1]["finished"] is True and seen[-1][1]["status"] == "error" and seen[-1][1]["error"] == "timed out"


def test_subagent_messages_are_ignored() -> None:
    seen, publish = collector()
    reporter = StreamReporter(publish, ServerRules(), ACTOR, "turn", Clock())
    reporter.feed(
        StreamEvent(
            uuid="u",
            session_id="s",
            event={"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "x", "name": "n"}},
            parent_tool_use_id="p",
        )
    )
    reporter.feed(AssistantMessage(content=[TextBlock(text="hidden")], model="m", parent_tool_use_id="p"))
    assert seen == []


def result_message() -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=False,
        num_turns=1,
        session_id="s",
        usage={"input_tokens": 1, "output_tokens": 1},
        total_cost_usd=0.0,
        result="done",
        structured_output={"accepted": True},
    )


async def test_client_streams_structured_progress_through_its_publisher() -> None:
    seen, publish = collector()

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        assert options.include_partial_messages is True
        yield partial({"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"accepted":true}'}})
        yield result_message()

    client = LlmClient(FixedRules(ServerRules(writing_emit_interval_ms=50)), enabled=True, query_function=fake_query, publish=publish)
    verdict = await client.structured("epic", "system", "prompt", output=Verdict)
    assert verdict.accepted is True
    assert kinds(seen) == [EventKind.AGENT_WRITING, EventKind.AGENT_WRITING]
    assert seen[-1][1]["finished"] is True and seen[-1][1]["status"] == "ok" and seen[-1][1]["who"] == "epic"


async def test_client_streams_agent_events_for_the_current_actor() -> None:
    seen, publish = collector()

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        yield AssistantMessage(content=[TextBlock(text="Thinking."), ToolUseBlock(id="a", name="mcp__aerona__look_around", input={})], model="m")
        yield result_message()

    client = LlmClient(FixedRules(ServerRules()), enabled=True, query_function=fake_query, publish=publish)
    token = current_actor.set(ACTOR)
    try:
        run = await client.run_agent("turn", "system", "prompt", tools=[])
    finally:
        current_actor.reset(token)
    assert run.completed
    assert kinds(seen) == [EventKind.AGENT_THOUGHT, EventKind.AGENT_TOOL_CALLED]
    assert all(payload["actor_id"] == 7 for _, payload in seen)
