import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pyte
import pytest

from aerona.catalog.providers import PROVIDERS, LoginDone, LoginSpec
from aerona.constants.providers import AGENT_PACKAGE_BIN
from aerona.domain.enums.providers import LoginState, ProviderKind
from aerona.services.providers.login import LoginRun, LoginRunner, Terminal
from aerona.services.providers.records import Connection
from tests.polling import until

FAKES = Path(__file__).with_name("fake_logins")
PROGRAMS = ("device", "token", "file", "fail", "raw")


def agents(tmp_path: Path) -> Path:
    folder = tmp_path / "agents" / AGENT_PACKAGE_BIN
    folder.mkdir(parents=True)
    for name in PROGRAMS:
        script = FAKES / f"{name}.py"
        program = folder / name
        program.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        program.chmod(0o755)
    return tmp_path / "agents"


def connection(tmp_path: Path, number: int) -> Connection:
    return Connection(number, 1, ProviderKind.CLAUDE_SUBSCRIPTION, "Claude", "", "", "", None, None, datetime.now(UTC), tmp_path / f"home{number}")


async def settled(run: LoginRun) -> LoginRun:
    assert await until(lambda: run.state is not LoginState.RUNNING), f"the login is still running: {run.output}"
    return run


@pytest.fixture
def finished() -> list[tuple[int, str]]:
    return []


def runner(tmp_path: Path, finished: list[tuple[int, str]]) -> LoginRunner:
    async def record(connection_id: int, secret: str) -> None:
        finished.append((connection_id, secret))

    return LoginRunner(agents(tmp_path), lambda home: {"PATH": os.environ["PATH"], "HOME": str(home)}, record)


async def test_a_device_login_shows_its_address_and_code_and_ends_on_exit(tmp_path: Path, finished: list[tuple[int, str]]) -> None:
    logins = runner(tmp_path, finished)
    run = await logins.start(connection(tmp_path, 1), LoginSpec("device", (), LoginDone.EXIT))
    await until(lambda: bool(run.code))
    assert run.links == ["https://example.test/device"] and run.code == "ABCD-1234" and "\x1b" not in run.output
    assert (await settled(run)).state is LoginState.SUCCEEDED
    assert finished == [(1, "")]


async def test_a_pasted_code_reaches_the_program_and_the_token_is_captured(tmp_path: Path, finished: list[tuple[int, str]]) -> None:
    logins = runner(tmp_path, finished)
    spec = PROVIDERS[ProviderKind.CLAUDE_SUBSCRIPTION].agent
    assert spec is not None
    run = await logins.start(connection(tmp_path, 2), LoginSpec("token", (), LoginDone.TOKEN, token_pattern=spec.login.token_pattern))
    await until(lambda: "Paste code" in run.output)
    await logins.send(2, "XYZ")
    assert (await settled(run)).state is LoginState.SUCCEEDED
    assert finished == [(2, "sk-ant-oat01-abcXYZDEF-ghi")]
    assert run.process is not None and run.process.returncode is not None


async def test_a_file_login_ends_when_its_file_appears(tmp_path: Path, finished: list[tuple[int, str]]) -> None:
    logins = runner(tmp_path, finished)
    run = await logins.start(connection(tmp_path, 3), LoginSpec("file", (), LoginDone.FILE, file=".gemini/creds.json"), {".gemini/settings.json": "{}"})
    await until(lambda: "authorization code" in run.output)
    await logins.send(3, "4/abc")
    assert (await settled(run)).state is LoginState.SUCCEEDED and finished == [(3, "")]


async def test_a_failed_a_cancelled_and_a_missing_login_say_so(tmp_path: Path, finished: list[tuple[int, str]]) -> None:
    logins = runner(tmp_path, finished)
    failed = await settled(await logins.start(connection(tmp_path, 4), LoginSpec("fail", (), LoginDone.EXIT)))
    assert failed.state is LoginState.FAILED and failed.note
    waiting = await logins.start(connection(tmp_path, 5), LoginSpec("file", (), LoginDone.FILE, file="never"))
    await logins.cancel(5)
    assert waiting.state is LoginState.CANCELLED and waiting.process is not None and waiting.process.returncode is not None
    missing = await logins.start(connection(tmp_path, 6), LoginSpec("nowhere", (), LoginDone.EXIT))
    assert missing.state is LoginState.FAILED and finished == []
    await logins.close()


async def test_a_long_code_pasted_into_a_raw_terminal_program_is_submitted(tmp_path: Path, finished: list[tuple[int, str]]) -> None:
    logins = runner(tmp_path, finished)
    spec = PROVIDERS[ProviderKind.CLAUDE_SUBSCRIPTION].agent
    assert spec is not None
    run = await logins.start(connection(tmp_path, 7), LoginSpec("raw", (), LoginDone.TOKEN, token_pattern=spec.login.token_pattern))
    await until(lambda: "Paste code here" in run.output)
    assert "Browser didn't open? Use the URL below" in run.output and run.links == ["https://example.test/oauth?code=true&state=abc"]
    assert "\u2500" not in run.output and "\u2502" not in run.output
    code = "A" * 43 + "#" + "B" * 43
    await logins.send(7, code)
    assert (await settled(run)).state is LoginState.SUCCEEDED, run.output
    assert finished == [(7, "sk-ant-oat01-" + code.replace("#", "_"))]


def test_the_screen_answers_terminal_queries_and_survives_every_private_sequence() -> None:
    answers: list[str] = []
    screen = Terminal(answers.append)
    finals = sorted(set(pyte.Stream.csi))
    for final in finals:
        screen.feed(f"\x1b[?1;2{final}\x1b[>4;?{final}\x1b[=1{final}".encode())
    screen.feed(b"\x1b[2J\x1b[H\x1b]8;id=1;https://a.test\x07link\x1b]8;;\x07\x1b[1C\x1b[32mok\x1b[0m\x1b[6n\x1b[c")
    assert screen.text().endswith("link ok")
    assert answers[-2:] == ["\x1b[1;8R", "\x1b[?6c"]
