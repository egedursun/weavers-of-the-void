import asyncio
import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import uvicorn
from mcp import types
from mcp.server.lowlevel.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.responses import PlainTextResponse
from starlette.types import Receive, Scope, Send

from aerona.constants.llm import TOOL_SERVER_NAME
from aerona.constants.providers import TOOL_GATE_PATH
from aerona.llm.tools import AgentTool

LOOPBACK = "127.0.0.1"
UNKNOWN_RUN = "This run has ended."
UNKNOWN_TOOL = "No such tool in this run."
NO_STREAM = PlainTextResponse("This gate sends no events.", status_code=405, headers={"allow": "POST"})


@dataclass(frozen=True)
class GatePass:
    token: str
    url: str


def token_of(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[-1]


class ToolGate:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, AgentTool]] = {}
        server: Server[Any] = Server(TOOL_SERVER_NAME, on_list_tools=self._list, on_call_tool=self._call)
        self._mcp = server
        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task[None] | None = None
        self._port = 0

    @property
    def running(self) -> bool:
        return self._port != 0

    def open(self, tools: Sequence[AgentTool]) -> GatePass:
        token = secrets.token_urlsafe(24)
        self._runs[token] = {tool.name: tool for tool in tools}
        return GatePass(token, f"http://{LOOPBACK}:{self._port}{TOOL_GATE_PATH}/{token}")

    def close(self, token: str) -> None:
        self._runs.pop(token, None)

    async def start(self) -> None:
        if self._server is not None:
            return
        manager = StreamableHTTPSessionManager(self._mcp, stateless=True, json_response=True)

        async def asgi(scope: Scope, receive: Receive, send: Send) -> None:
            if scope.get("method") == "GET":
                await NO_STREAM(scope, receive, send)
                return
            await manager.handle_request(scope, receive, send)

        server = uvicorn.Server(uvicorn.Config(asgi, host=LOOPBACK, port=0, log_level="warning", lifespan="off", interface="asgi3"))

        async def serve() -> None:
            async with manager.run():
                await server.serve()

        self._server = server
        self._task = asyncio.create_task(serve())
        while not server.started:
            if self._task.done():
                await self._task
            await asyncio.sleep(0.01)
        self._port = int(server.servers[0].sockets[0].getsockname()[1])

    async def stop(self) -> None:
        if self._server is not None and self._task is not None:
            self._server.should_exit = True
            await self._task
        self._server = None
        self._task = None
        self._port = 0

    def _tools_of(self, context: Any) -> dict[str, AgentTool] | None:
        request = getattr(context, "request", None)
        path = getattr(getattr(request, "url", None), "path", "")
        return self._runs.get(token_of(str(path)))

    async def _list(self, context: Any, params: Any) -> types.ListToolsResult:
        del params
        tools = self._tools_of(context) or {}
        return types.ListToolsResult(
            tools=[types.Tool(name=tool.name, description=tool.description, input_schema=tool.input_schema) for tool in tools.values()]
        )

    async def _call(self, context: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        tools = self._tools_of(context)
        if tools is None:
            return types.CallToolResult(content=[types.TextContent(type="text", text=UNKNOWN_RUN)], is_error=True)
        tool = tools.get(params.name)
        if tool is None:
            return types.CallToolResult(content=[types.TextContent(type="text", text=UNKNOWN_TOOL)], is_error=True)
        reply = await tool.handler(dict(params.arguments or {}))
        return types.CallToolResult(content=[types.TextContent(type="text", text=reply.text)], is_error=reply.is_error)
