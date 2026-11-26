import asyncio
import json
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from aerona.llm.backends.acp import AcpBackend, AgentLaunch, tool_named
from aerona.llm.backends.base import RunRequest, StopReason
from aerona.llm.errors import LlmTransientError, LlmUnavailableError
from aerona.llm.events import ReplyEnded, RunEvent, ToolPreparing
from aerona.llm.tool_gate import ToolGate
from aerona.llm.tools import AgentTool, ToolReply

FAKE = Path(__file__).with_name("fake_acp_agent.py")
SCHEMA = {"type": "object", "properties": {"name": {"type": "string"}}}


def launch(tmp_path: Path, mode: str, answer: dict[str, Any] | None = None, *, marked: bool = True) -> AgentLaunch:
    program = tmp_path / "agent"
    program.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" "$@"\n', encoding="utf-8")
    program.chmod(0o755)
    environment = {"PATH": os.environ["PATH"], "FAKE_MODE": mode, "FAKE_LOG": str(tmp_path / "log.jsonl"), "FAKE_ANSWER": json.dumps(answer or {})}
    return AgentLaunch(
        program,
        (),
        environment,
        tmp_path / "home",
        files={".agent/settings.json": "{}"},
        auth_method="login",
        session_meta={"plain": True},
        session_mode="careful",
        marks_messages=marked,
    )


def logged(tmp_path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()]


@pytest.fixture
async def gate() -> AsyncIterator[ToolGate]:
    found = ToolGate()
    await found.start()
    yield found
    await found.stop()


def star_tool(heard: list[dict[str, Any]], stop: asyncio.Event | None = None) -> AgentTool:
    async def handler(arguments: dict[str, Any]) -> ToolReply:
        heard.append(arguments)
        if stop is not None:
            stop.set()
        return ToolReply("Vela burns blue")

    return AgentTool("lookup_star", "Look up a star", SCHEMA, handler)


async def test_a_run_reaches_the_tool_through_the_gate_and_streams_replies(tmp_path: Path, gate: ToolGate) -> None:
    backend = AcpBackend(launch(tmp_path, "tool"), gate)
    heard: list[dict[str, Any]] = []
    events: list[RunEvent] = []
    try:
        end = await backend.run(RunRequest("Be brief.", "Find Vela.", (star_tool(heard),), "m2", 5), events.append, asyncio.Event())
    finally:
        await backend.close()
    assert end.stop is StopReason.COMPLETED and end.turns == 2
    assert heard == [{"name": "Vela"}]
    assert ToolPreparing("tc1", "lookup_star") in events
    assert [event.text for event in events if isinstance(event, ReplyEnded)] == ["Let me look.", "Found: Vela burns blue"]
    entries = logged(tmp_path)
    new = next(entry for entry in entries if entry.get("method") == "session/new")["params"]
    assert new["systemPrompt"]["content"][0]["text"] == "Be brief."
    assert new["_meta"] == {"plain": True} and new["mcpServers"][0]["type"] == "http"
    assert {"method": "session/set_config_option", "params": {"sessionId": "s1", "configId": "model", "value": "m2"}} in entries
    assert any(entry.get("method") == "session/close" for entry in entries)
    assert {"method": "session/set_mode", "params": {"sessionId": "s1", "modeId": "careful"}} in entries
    assert (tmp_path / "home" / ".agent" / "settings.json").exists()


async def test_a_permission_for_anything_but_the_run_tools_is_refused(tmp_path: Path, gate: ToolGate) -> None:
    backend = AcpBackend(launch(tmp_path, "forbidden"), gate)
    heard: list[dict[str, Any]] = []
    events: list[RunEvent] = []
    try:
        await backend.run(RunRequest("", "List files.", (star_tool(heard),), "", 5), events.append, asyncio.Event())
    finally:
        await backend.close()
    assert heard == []
    assert {"permission": "run_shell_command", "outcome": {"outcome": "selected", "optionId": "no"}} in logged(tmp_path)
    assert [event.text for event in events if isinstance(event, ReplyEnded)][-1] == "rejected"


async def test_a_run_stops_at_its_step_limit(tmp_path: Path, gate: ToolGate) -> None:
    backend = AcpBackend(launch(tmp_path, "loop"), gate)
    heard: list[dict[str, Any]] = []
    try:
        end = await backend.run(RunRequest("", "Keep going.", (star_tool(heard),), "", 3), lambda event: None, asyncio.Event())
    finally:
        await backend.close()
    assert end.stop is StopReason.STEP_LIMIT
    assert 2 <= len(heard) <= 3
    assert any(entry.get("method") == "session/cancel" for entry in logged(tmp_path))


async def test_every_model_message_that_only_calls_a_tool_still_counts_as_a_reply(tmp_path: Path, gate: ToolGate) -> None:
    backend = AcpBackend(launch(tmp_path, "loop"), gate)
    events: list[RunEvent] = []
    try:
        end = await backend.run(RunRequest("", "Keep going.", (star_tool([]),), "", 4), events.append, asyncio.Event())
    finally:
        await backend.close()
    replies = [event.text for event in events if isinstance(event, ReplyEnded)]
    assert replies[0] == "Let me look." and set(replies[1:]) == {""} and len(replies) == end.turns >= 3


async def test_a_run_stops_when_asked(tmp_path: Path, gate: ToolGate) -> None:
    backend = AcpBackend(launch(tmp_path, "loop"), gate)
    heard: list[dict[str, Any]] = []
    stop = asyncio.Event()
    try:
        end = await backend.run(RunRequest("", "Keep going.", (star_tool(heard, stop),), "", 50), lambda event: None, stop)
    finally:
        await backend.close()
    assert end.stop is StopReason.STOPPED and len(heard) == 1


async def test_a_refused_login_is_unavailable_and_a_rate_limit_is_transient(tmp_path: Path, gate: ToolGate) -> None:
    refused = AcpBackend(launch(tmp_path, "refuse"), gate)
    with pytest.raises(LlmUnavailableError):
        await refused.run(RunRequest("", "Hi.", (), "", 2), lambda event: None, asyncio.Event())
    await refused.close()
    limited = AcpBackend(launch(tmp_path, "quota"), gate)
    try:
        with pytest.raises(LlmTransientError):
            await limited.run(RunRequest("", "Hi.", (star_tool([]),), "", 2), lambda event: None, asyncio.Event())
    finally:
        await limited.close()


async def test_the_agent_lists_its_models_and_a_missing_agent_is_unavailable(tmp_path: Path, gate: ToolGate) -> None:
    backend = AcpBackend(launch(tmp_path, "tool"), gate)
    try:
        assert await backend.models() == ["m1", "m2"]
    finally:
        await backend.close()
    missing = AcpBackend(AgentLaunch(tmp_path / "nowhere", (), {}, tmp_path / "away"), gate)
    with pytest.raises(LlmUnavailableError):
        await missing.models()


async def test_an_agent_that_marks_its_messages_keeps_its_notes_out_and_one_that_does_not_keeps_them(tmp_path: Path, gate: ToolGate) -> None:
    unmarked = AcpBackend(launch(tmp_path, "tool", marked=False), gate)
    events: list[RunEvent] = []
    try:
        await unmarked.run(RunRequest("", "Find Vela.", (star_tool([]),), "", 5), events.append, asyncio.Event())
    finally:
        await unmarked.close()
    assert next(event.text for event in events if isinstance(event, ReplyEnded)) == "Info: some tools are switched offLet me look."


async def test_a_permission_without_a_title_is_matched_by_its_call(tmp_path: Path, gate: ToolGate) -> None:
    backend = AcpBackend(launch(tmp_path, "untitled"), gate)
    heard: list[dict[str, Any]] = []
    try:
        await backend.run(RunRequest("", "Find Vela.", (star_tool(heard),), "", 5), lambda event: None, asyncio.Event())
    finally:
        await backend.close()
    assert heard == [{"name": "Vela"}]


def test_tool_names_are_found_behind_every_agent_prefix() -> None:
    names = frozenset({"lookup_star", "answer"})
    titles = (
        "answer",
        "aerona-lookup_star",
        "mcp__aerona__answer",
        "mcp_aerona_lookup_star",
        "mcp.aerona.answer",
        "aerona: answer",
        "lookup_star(name: Vela)",
        "run_shell_command",
    )
    assert [tool_named(title, names) for title in titles] == ["answer", "lookup_star", "answer", "lookup_star", "answer", "answer", "lookup_star", None]
