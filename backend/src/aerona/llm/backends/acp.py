import asyncio
import base64
import contextlib
import json
import logging
from collections import deque
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aerona.constants.llm import TOOL_SERVER_NAME
from aerona.constants.providers import AGENT_START_SECONDS
from aerona.llm.backends.base import RunEnd, RunRequest, StopReason
from aerona.llm.errors import LlmError, LlmTransientError, LlmUnavailableError
from aerona.llm.events import EventSink, ReplyEnded, TextDelta, ThoughtDelta, ToolPreparing
from aerona.llm.tool_gate import ToolGate

LOGGER = logging.getLogger(__name__)
PROTOCOL_VERSION = 1
STDERR_LINES = 40
NOTE_CHARS = 300
FINISHED_CALLS = frozenset({"completed", "failed"})
STREAM_LIMIT = 1 << 24
CANCEL_SECONDS = 30
NOT_SUPPORTED = -32601
TOOL_SEPARATORS = ("__", "_", "-", "/", ".", ":", " ")
REFUSING_WORDS = ("auth", "login", "log in", "credential", "401", "403", "forbidden", "unauthor")
STOPS = {
    "end_turn": StopReason.COMPLETED,
    "max_tokens": StopReason.STEP_LIMIT,
    "max_turn_requests": StopReason.STEP_LIMIT,
    "refusal": StopReason.REFUSED,
    "cancelled": StopReason.STOPPED,
}


class AcpRequestError(Exception):
    def __init__(self, method: str, code: int, message: str) -> None:
        super().__init__(f"{method}: {message} ({code})")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AgentLaunch:
    program: Path
    arguments: tuple[str, ...]
    environment: Mapping[str, str]
    home: Path
    files: Mapping[str, str] = field(default_factory=dict)
    auth_method: str = ""
    session_meta: Mapping[str, object] = field(default_factory=dict)
    session_mode: str = ""
    marks_messages: bool = False


def tool_named(title: str, names: frozenset[str]) -> str | None:
    text = title.split("(", 1)[0].strip()
    if text in names:
        return text
    for name in names:
        if any(text.endswith(f"{separator}{name}") for separator in TOOL_SEPARATORS):
            return name
    return None


def refused(message: str) -> bool:
    lowered = message.lower()
    return any(word in lowered for word in REFUSING_WORDS)


def prompt_blocks(request: RunRequest, system_in_prompt: bool, images: bool) -> list[dict[str, Any]]:
    text = f"{request.system}\n\n{request.prompt}" if system_in_prompt and request.system else request.prompt
    blocks: list[dict[str, Any]] = [{"type": "text", "text": text}]
    if images:
        blocks.extend({"type": "image", "mimeType": image.media_type, "data": base64.b64encode(image.data).decode("ascii")} for image in request.images)
    return blocks


@dataclass
class SessionRun:
    events: EventSink
    names: frozenset[str]
    max_turns: int
    stop: asyncio.Event
    marked: bool = False
    titles: dict[str, str] = field(default_factory=dict)
    text: list[str] = field(default_factory=list)
    thoughts: list[str] = field(default_factory=list)
    message_id: str | None = None
    replies: int = 0
    tool_calls: int = 0
    limited: bool = False
    after_tool: bool = False

    def flush(self) -> None:
        if self.text or self.thoughts:
            self.events(ReplyEnded("".join(self.text), "".join(self.thoughts)))
            self.replies += 1
        self.text.clear()
        self.thoughts.clear()

    def reply_before_tool(self) -> None:
        if self.text or self.thoughts:
            self.flush()
        elif not self.after_tool:
            self.events(ReplyEnded("", ""))
            self.replies += 1

    def chunk(self, update: dict[str, Any], *, thought: bool) -> None:
        content = update.get("content") or {}
        text = content.get("text") if isinstance(content, dict) else None
        if not isinstance(text, str) or not text:
            return
        message_id = update.get("messageId")
        if self.marked and message_id is None:
            LOGGER.info("The agent noted: %s", text.strip()[:NOTE_CHARS])
            return
        if message_id is not None and self.message_id is not None and message_id != self.message_id:
            self.flush()
        self.message_id = message_id if message_id is not None else self.message_id
        self.after_tool = False
        (self.thoughts if thought else self.text).append(text)
        self.events(ThoughtDelta(text) if thought else TextDelta(text))

    def tool(self, update: dict[str, Any]) -> None:
        self.reply_before_tool()
        self.after_tool = True
        self.message_id = None
        self.tool_calls += 1
        title = str(update.get("title") or "")
        call_id = str(update.get("toolCallId") or "")
        self.titles[call_id] = title
        self.events(ToolPreparing(call_id, tool_named(title, self.names) or title))
        if self.tool_calls >= self.max_turns:
            self.limited = True
            self.stop.set()


RequestHandler = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class JsonRpc:
    def __init__(self, process: asyncio.subprocess.Process, on_request: RequestHandler, on_notice: Callable[[str, dict[str, Any]], None]) -> None:
        self._process = process
        self._on_request = on_request
        self._on_notice = on_notice
        self._next = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._stderr: deque[str] = deque(maxlen=STDERR_LINES)
        self._tasks = [asyncio.create_task(self._read()), asyncio.create_task(self._drain())]
        self._replies: set[asyncio.Task[None]] = set()

    @property
    def alive(self) -> bool:
        return self._process.returncode is None

    def last_words(self) -> str:
        return " ".join(self._stderr)[-600:]

    async def request(self, method: str, params: dict[str, Any], seconds: float | None = None) -> dict[str, Any]:
        self._next += 1
        number = self._next
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[number] = future
        await self._send({"jsonrpc": "2.0", "id": number, "method": method, "params": params})
        try:
            message = await asyncio.wait_for(future, seconds)
        finally:
            self._pending.pop(number, None)
        if "error" in message:
            error = message["error"] or {}
            raise AcpRequestError(method, int(error.get("code", 0)), str(error.get("message", "")))
        result = message.get("result")
        return result if isinstance(result, dict) else {}

    async def notify(self, method: str, params: dict[str, Any]) -> None:
        await self._send({"jsonrpc": "2.0", "method": method, "params": params})

    async def close(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self.alive:
            self._process.kill()
            with contextlib.suppress(ProcessLookupError):
                await self._process.wait()

    async def _send(self, message: dict[str, Any]) -> None:
        stdin = self._process.stdin
        if stdin is None or not self.alive:
            raise LlmTransientError(f"the agent stopped: {self.last_words()}")
        stdin.write((json.dumps(message) + "\n").encode())
        await stdin.drain()

    async def _read(self) -> None:
        stdout = self._process.stdout
        assert stdout is not None
        while line := await stdout.readline():
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(message, dict):
                continue
            if "method" in message and "id" in message:
                task = asyncio.create_task(self._answer(message))
                self._replies.add(task)
                task.add_done_callback(self._replies.discard)
            elif "method" in message:
                self._on_notice(str(message["method"]), message.get("params") or {})
            elif message.get("id") in self._pending:
                self._pending[message["id"]].set_result(message)
        for future in self._pending.values():
            if not future.done():
                future.set_exception(LlmTransientError(f"the agent stopped: {self.last_words()}"))

    async def _answer(self, message: dict[str, Any]) -> None:
        try:
            result = await self._on_request(str(message["method"]), message.get("params") or {})
            await self._send({"jsonrpc": "2.0", "id": message["id"], "result": result})
        except AcpRequestError as error:
            await self._send({"jsonrpc": "2.0", "id": message["id"], "error": {"code": error.code, "message": error.message}})

    async def _drain(self) -> None:
        stderr = self._process.stderr
        assert stderr is not None
        while line := await stderr.readline():
            self._stderr.append(line.decode(errors="replace").strip())


def lay_files(home: Path, files: Mapping[str, str]) -> None:
    home.mkdir(parents=True, exist_ok=True)
    for relative, text in files.items():
        target = home / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


class AcpBackend:
    def __init__(self, launch: AgentLaunch, gate: ToolGate) -> None:
        self._launch = launch
        self._gate = gate
        self._rpc: JsonRpc | None = None
        self._capabilities: dict[str, Any] = {}
        self._runs: dict[str, SessionRun] = {}
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        if self._rpc is not None:
            await self._rpc.close()
            self._rpc = None

    async def models(self) -> list[str]:
        rpc = await self._ready()
        session = await self._new_session(rpc, None)
        try:
            return choices(session)
        finally:
            await self._end_session(rpc, str(session.get("sessionId", "")))

    async def run(self, request: RunRequest, events: EventSink, stop: asyncio.Event) -> RunEnd:
        rpc = await self._ready()
        passed = self._gate.open(request.tools)
        try:
            session = await self._new_session(rpc, passed.url, request.system)
            session_id = str(session["sessionId"])
            run = SessionRun(events, frozenset(tool.name for tool in request.tools), max(1, request.max_turns), stop, self._launch.marks_messages)
            self._runs[session_id] = run
            try:
                await self._choose_mode(rpc, session, session_id)
                await self._choose_model(rpc, session, session_id, request.model)
                return await self._prompt(rpc, session_id, request, run)
            finally:
                self._runs.pop(session_id, None)
                await self._end_session(rpc, session_id)
        except AcpRequestError as error:
            raise self._failure(error) from error
        finally:
            self._gate.close(passed.token)

    async def _prompt(self, rpc: JsonRpc, session_id: str, request: RunRequest, run: SessionRun) -> RunEnd:
        caps = self._capabilities
        images = bool(request.images) and bool((caps.get("promptCapabilities") or {}).get("image"))
        blocks = prompt_blocks(request, not self._takes_system_prompt(), images)
        prompting = asyncio.create_task(rpc.request("session/prompt", {"sessionId": session_id, "prompt": blocks}))
        stopping = asyncio.create_task(run.stop.wait())
        try:
            await asyncio.wait({prompting, stopping}, return_when=asyncio.FIRST_COMPLETED)
            if not prompting.done():
                await rpc.notify("session/cancel", {"sessionId": session_id})
                with contextlib.suppress(TimeoutError, AcpRequestError, LlmError):
                    await asyncio.wait_for(asyncio.shield(prompting), CANCEL_SECONDS)
                run.flush()
                return RunEnd(StopReason.STEP_LIMIT if run.limited else StopReason.STOPPED, run.replies)
            result = prompting.result()
        finally:
            stopping.cancel()
            if not prompting.done():
                prompting.cancel()
        run.flush()
        stop = StopReason.STEP_LIMIT if run.limited else STOPS.get(str(result.get("stopReason")), StopReason.COMPLETED)
        return RunEnd(stop, run.replies)

    async def _ready(self) -> JsonRpc:
        async with self._lock:
            if self._rpc is not None and self._rpc.alive:
                return self._rpc
            if self._rpc is not None:
                await self._rpc.close()
            self._rpc = await self._start()
            return self._rpc

    async def _start(self) -> JsonRpc:
        launch = self._launch
        lay_files(launch.home, launch.files)
        if not launch.program.exists():
            raise LlmUnavailableError(f"the agent is not installed at {launch.program}")
        process = await asyncio.create_subprocess_exec(
            str(launch.program),
            *launch.arguments,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=dict(launch.environment),
            cwd=str(launch.home),
            limit=STREAM_LIMIT,
        )
        rpc = JsonRpc(process, self._answer, self._notice)
        try:
            found = await rpc.request(
                "initialize",
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False}, "terminal": False},
                    "clientInfo": {"name": TOOL_SERVER_NAME, "version": "1"},
                },
                AGENT_START_SECONDS,
            )
            self._capabilities = found.get("agentCapabilities") or {}
            if launch.auth_method:
                await rpc.request("authenticate", {"methodId": launch.auth_method}, AGENT_START_SECONDS)
        except (AcpRequestError, TimeoutError, LlmError) as error:
            words = rpc.last_words()
            await rpc.close()
            raise LlmUnavailableError(f"the agent did not start: {error} {words}".strip()) from error
        return rpc

    def _takes_system_prompt(self) -> bool:
        return "systemPrompt" in (self._capabilities.get("sessionCapabilities") or {})

    def _system_mode(self) -> str:
        mode = ((self._capabilities.get("sessionCapabilities") or {}).get("systemPrompt") or {}).get("mode") or {}
        return "override" if "override" in mode else "append"

    async def _new_session(self, rpc: JsonRpc, gate_url: str | None, system: str = "") -> dict[str, Any]:
        servers = [{"type": "http", "name": TOOL_SERVER_NAME, "url": gate_url, "headers": []}] if gate_url else []
        params: dict[str, Any] = {"cwd": str(self._launch.home), "mcpServers": servers}
        if self._launch.session_meta:
            params["_meta"] = dict(self._launch.session_meta)
        if system and self._takes_system_prompt():
            params["systemPrompt"] = {"mode": self._system_mode(), "content": [{"type": "text", "text": system}]}
        return await rpc.request("session/new", params, AGENT_START_SECONDS)

    async def _choose_model(self, rpc: JsonRpc, session: dict[str, Any], session_id: str, model: str) -> None:
        if not model:
            return
        option = model_option(session)
        if option is not None:
            await rpc.request("session/set_config_option", {"sessionId": session_id, "configId": option, "value": model}, AGENT_START_SECONDS)
        elif session.get("models"):
            await rpc.request("session/set_model", {"sessionId": session_id, "modelId": model}, AGENT_START_SECONDS)

    async def _choose_mode(self, rpc: JsonRpc, session: dict[str, Any], session_id: str) -> None:
        wanted = self._launch.session_mode
        offered = {str(mode.get("id")) for mode in (session.get("modes") or {}).get("availableModes") or () if isinstance(mode, dict)}
        if wanted and wanted in offered:
            await rpc.request("session/set_mode", {"sessionId": session_id, "modeId": wanted}, AGENT_START_SECONDS)

    async def _end_session(self, rpc: JsonRpc, session_id: str) -> None:
        if session_id and "close" in (self._capabilities.get("sessionCapabilities") or {}) and rpc.alive:
            with contextlib.suppress(AcpRequestError, TimeoutError, LlmError):
                await rpc.request("session/close", {"sessionId": session_id}, CANCEL_SECONDS)

    def _failure(self, error: AcpRequestError) -> LlmError:
        return LlmUnavailableError(error.message) if refused(error.message) else LlmTransientError(str(error))

    async def _answer(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method != "session/request_permission":
            raise AcpRequestError(method, NOT_SUPPORTED, "not offered")
        run = self._runs.get(str(params.get("sessionId", "")))
        call = params.get("toolCall") or {}
        title = str(call.get("title") or (run.titles.get(str(call.get("toolCallId") or ""), "") if run is not None else ""))
        allowed = run is not None and tool_named(title, run.names) is not None
        wanted = "allow" if allowed else "reject"
        options = [option for option in params.get("options") or [] if isinstance(option, dict)]
        chosen = next((option for option in options if str(option.get("kind", "")).startswith(f"{wanted}_once")), None)
        chosen = chosen or next((option for option in options if str(option.get("kind", "")).startswith(wanted)), None)
        if chosen is None:
            return {"outcome": {"outcome": "cancelled"}}
        return {"outcome": {"outcome": "selected", "optionId": chosen["optionId"]}}

    def _notice(self, method: str, params: dict[str, Any]) -> None:
        if method != "session/update":
            return
        run = self._runs.get(str(params.get("sessionId", "")))
        update = params.get("update") or {}
        if run is None or not isinstance(update, dict):
            return
        kind = update.get("sessionUpdate")
        if kind == "agent_message_chunk":
            run.chunk(update, thought=False)
        elif kind == "agent_thought_chunk":
            run.chunk(update, thought=True)
        elif kind == "tool_call":
            run.tool(update)
        elif kind == "tool_call_update" and update.get("status") in FINISHED_CALLS:
            run.after_tool = False


def model_option(session: Mapping[str, Any]) -> str | None:
    for option in session.get("configOptions") or ():
        if isinstance(option, dict) and option.get("category") == "model":
            return str(option.get("id"))
    return None


def choices(session: Mapping[str, Any]) -> list[str]:
    for option in session.get("configOptions") or ():
        if isinstance(option, dict) and option.get("category") == "model":
            return [str(item.get("value")) for item in option.get("options") or () if isinstance(item, dict) and item.get("value")]
    models = session.get("models") or {}
    return [str(item.get("modelId")) for item in models.get("availableModels") or () if isinstance(item, dict) and item.get("modelId")]
