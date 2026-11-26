import asyncio
import contextlib
import inspect
import os
import re
import shutil
import signal
import struct
import sys
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

if sys.platform != "win32":
    import fcntl
    import termios

import pyte

from aerona.catalog.providers import HOME, LoginDone, LoginSpec
from aerona.constants.providers import AGENT_PACKAGE_BIN, LOGIN_OUTPUT_MAX_CHARS, LOGIN_SECONDS
from aerona.domain.enums.providers import LoginState
from aerona.llm.backends.acp import lay_files
from aerona.services.providers.records import Connection

BOX_EDGES = "".join(chr(point) for point in range(0x2500, 0x2580))
LINKS = re.compile(r"https://[^\s\"'<>\x1b]+")
CODES = re.compile(r"\b[A-Z0-9]{4,5}-[A-Z0-9]{4,5}\b")
READ_SIZE = 4096
NO_BROWSER_DIRNAME = ".no-browser"
AUTOMATION_VARIABLES = frozenset({"CI", "NO_COLOR"})
LOGIN_TERMINAL = "xterm-256color"
BROWSER_OPENERS = ("open", "xdg-open", "wslview", "sensible-browser", "x-www-browser", "gnome-open")
TERMINAL_ROWS = 50
TERMINAL_COLUMNS = 1000
POLL_SECONDS = 1.0
KEY_GAP_SECONDS = 0.5
ENTER = b"\r"
HISTORY_LINES = 2000
ANSWER_HOOK = "write_process_input"
STOP_SECONDS = 5
NO_TERMINAL = "Logging in needs a terminal, which this server does not offer."
NOT_INSTALLED = "The login program is not installed."
TIMED_OUT = "The login took too long and was stopped."
EXITED = "The login program stopped without logging in."

Finished = Callable[[int, str], Awaitable[None]]


def widen(terminal: int) -> None:
    if sys.platform != "win32":
        with contextlib.suppress(OSError):
            fcntl.ioctl(terminal, termios.TIOCSWINSZ, struct.pack("HHHH", TERMINAL_ROWS, TERMINAL_COLUMNS, 0, 0))


def tidy(lines: list[str]) -> str:
    kept: list[str] = []
    for line in lines:
        bare = line.strip().strip(BOX_EDGES).strip()
        if bare or (kept and kept[-1]):
            kept.append(bare)
    return "\n".join(kept).strip()


def takes_private(handler: Callable[..., object]) -> bool:
    parameters = inspect.signature(handler).parameters.values()
    return any(parameter.name == "private" or parameter.kind is parameter.VAR_KEYWORD for parameter in parameters)


UNREADABLE_SEQUENCE = (TypeError, ValueError, LookupError, NameError, ArithmeticError)


def forgiving(handler: Callable[..., object], private_aware: bool) -> Callable[..., object]:
    def handle(*arguments: object, **options: object) -> object:
        if options.get("private") and not private_aware:
            return None
        try:
            return handler(*arguments, **options) if private_aware else handler(*arguments)
        except UNREADABLE_SEQUENCE:
            return None

    return handle


class AnsweringScreen(pyte.HistoryScreen):
    def __init__(self, answer: Callable[[str], None]) -> None:
        super().__init__(TERMINAL_COLUMNS, TERMINAL_ROWS, history=HISTORY_LINES)
        setattr(self, ANSWER_HOOK, answer)
        for name in sorted(pyte.Stream.events):
            original = getattr(pyte.Screen, name, None)
            if original is not None and name != "draw":
                setattr(self, name, forgiving(object.__getattribute__(self, name), takes_private(original)))


class Terminal:
    def __init__(self, answer: Callable[[str], None] = lambda data: None) -> None:
        self._screen = AnsweringScreen(answer)
        self._stream = pyte.ByteStream(self._screen)

    def feed(self, chunk: bytes) -> None:
        self._stream.feed(chunk)

    def text(self) -> str:
        columns = self._screen.columns
        scrolled = ["".join(line[column].data for column in range(columns)) for line in self._screen.history.top]
        return tidy([*scrolled, *self._screen.display])


@dataclass
class LoginRun:
    connection_id: int
    started_at: datetime
    state: LoginState = LoginState.RUNNING
    output: str = ""
    note: str = ""
    ended_at: datetime | None = None
    process: asyncio.subprocess.Process | None = field(default=None, repr=False)
    terminal: int | None = field(default=None, repr=False)
    screen: Terminal = field(default_factory=Terminal, repr=False)
    tasks: list[asyncio.Task[None]] = field(default_factory=list, repr=False)

    @property
    def links(self) -> list[str]:
        return list(dict.fromkeys(LINKS.findall(self.output)))

    @property
    def code(self) -> str:
        found = CODES.findall(self.output)
        return found[-1] if found else ""

    def hear(self, chunk: bytes) -> None:
        self.screen.feed(chunk)
        self.output = self.screen.text()[-LOGIN_OUTPUT_MAX_CHARS:]

    def end(self, state: LoginState, note: str = "") -> None:
        if self.state is LoginState.RUNNING:
            self.state = state
            self.note = note
            self.ended_at = datetime.now(UTC)


def answer(run: LoginRun, data: str) -> None:
    if run.terminal is not None:
        with contextlib.suppress(OSError):
            os.write(run.terminal, data.encode())


def browserless(home: Path) -> Path:
    folder = home / NO_BROWSER_DIRNAME
    folder.mkdir(parents=True, exist_ok=True)
    for name in BROWSER_OPENERS:
        opener = folder / name
        opener.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        opener.chmod(0o755)
    return folder


def login_environment(spec: LoginSpec, home: Path, base: dict[str, str]) -> dict[str, str]:
    environment = {name: value for name, value in base.items() if name not in AUTOMATION_VARIABLES}
    environment["TERM"] = LOGIN_TERMINAL
    environment.update({name: value.replace(HOME, str(home)) for name, value in spec.environment.items()})
    environment["PATH"] = os.pathsep.join(part for part in (str(browserless(home)), environment.get("PATH", "")) if part)
    return environment


class LoginRunner:
    def __init__(self, agents_dir: Path, base_environment: Callable[[Path], dict[str, str]], finished: Finished) -> None:
        self._agents_dir = agents_dir
        self._base = base_environment
        self._finished = finished
        self._runs: dict[int, LoginRun] = {}

    def view(self, connection_id: int) -> LoginRun | None:
        return self._runs.get(connection_id)

    async def start(self, connection: Connection, spec: LoginSpec, files: Mapping[str, str] | None = None) -> LoginRun:
        await self.cancel(connection.id)
        run = LoginRun(connection.id, datetime.now(UTC))
        self._runs[connection.id] = run
        program = self._agents_dir / AGENT_PACKAGE_BIN / spec.program
        if not hasattr(os, "openpty"):
            run.end(LoginState.FAILED, NO_TERMINAL)
            return run
        if not program.exists():
            run.end(LoginState.FAILED, NOT_INSTALLED)
            return run
        lay_files(connection.home, files or {})
        leader, follower = os.openpty()
        widen(follower)
        try:
            run.process = await asyncio.create_subprocess_exec(
                str(program),
                *spec.arguments,
                stdin=follower,
                stdout=follower,
                stderr=follower,
                env=login_environment(spec, connection.home, self._base(connection.home)),
                cwd=str(connection.home),
                start_new_session=True,
            )
        finally:
            os.close(follower)
        run.terminal = leader
        run.screen = Terminal(lambda data: answer(run, data))
        run.tasks = [asyncio.create_task(self._read(run)), asyncio.create_task(self._watch(run, connection.home, spec))]
        return run

    async def send(self, connection_id: int, text: str) -> LoginRun | None:
        run = self._runs.get(connection_id)
        if run is not None and run.state is LoginState.RUNNING and run.terminal is not None:
            if text:
                os.write(run.terminal, text.encode())
                await asyncio.sleep(KEY_GAP_SECONDS)
            if run.terminal is not None:
                os.write(run.terminal, ENTER)
        return run

    async def cancel(self, connection_id: int) -> None:
        run = self._runs.get(connection_id)
        if run is None:
            return
        run.end(LoginState.CANCELLED)
        await self._stop(run)

    async def close(self) -> None:
        for connection_id in list(self._runs):
            await self.cancel(connection_id)

    async def _read(self, run: LoginRun) -> None:
        loop = asyncio.get_running_loop()
        terminal = run.terminal
        while terminal is not None:
            try:
                chunk = await loop.run_in_executor(None, os.read, terminal, READ_SIZE)
            except OSError:
                return
            if not chunk:
                return
            run.hear(chunk)

    async def _watch(self, run: LoginRun, home: Path, spec: LoginSpec) -> None:
        process = run.process
        assert process is not None
        deadline = asyncio.get_running_loop().time() + LOGIN_SECONDS
        pattern = re.compile(spec.token_pattern) if spec.token_pattern else None
        while run.state is LoginState.RUNNING:
            secret = self._found(run, home, spec, pattern)
            if secret is not None:
                await self._succeed(run, secret)
                return
            if process.returncode is not None:
                await asyncio.sleep(POLL_SECONDS)
                secret = self._found(run, home, spec, pattern)
                if secret is not None:
                    await self._succeed(run, secret)
                elif spec.done is LoginDone.EXIT and process.returncode == 0:
                    await self._succeed(run, "")
                else:
                    run.end(LoginState.FAILED, EXITED)
                return
            if asyncio.get_running_loop().time() > deadline:
                run.end(LoginState.FAILED, TIMED_OUT)
                await self._stop(run)
                return
            await asyncio.sleep(POLL_SECONDS)

    @staticmethod
    def _found(run: LoginRun, home: Path, spec: LoginSpec, pattern: re.Pattern[str] | None) -> str | None:
        if spec.done is LoginDone.TOKEN and pattern is not None:
            match = pattern.search(run.output)
            return match.group(1) if match is not None else None
        if spec.done is LoginDone.FILE and (home / spec.file).exists():
            return ""
        return None

    async def _succeed(self, run: LoginRun, secret: str) -> None:
        await self._finished(run.connection_id, secret)
        run.end(LoginState.SUCCEEDED)
        await self._stop(run)

    async def _stop(self, run: LoginRun) -> None:
        process = run.process
        if process is not None and process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                await asyncio.wait_for(process.wait(), STOP_SECONDS)
            except TimeoutError:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                await process.wait()
        if run.terminal is not None:
            with contextlib.suppress(OSError):
                os.close(run.terminal)
            run.terminal = None
        current = asyncio.current_task()
        for task in run.tasks:
            if task is not current:
                task.cancel()


def forget_login(home: Path) -> None:
    shutil.rmtree(home, ignore_errors=True)
