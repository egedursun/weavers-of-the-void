import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

Reply = Callable[[dict[str, Any]], dict[str, Any]]


def chunk(model: str, delta: dict[str, Any], finish: str | None) -> str:
    body = {"id": "c", "object": "chat.completion.chunk", "created": 1, "model": model, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
    return f"data: {json.dumps(body)}\n\n"


def calls_first_tool(body: dict[str, Any]) -> dict[str, Any]:
    tools = [tool["function"]["name"] for tool in body.get("tools", [])]
    if tools and not any(message["role"] == "tool" for message in body["messages"]):
        return {"tool_calls": [{"index": 0, "id": "call_a", "type": "function", "function": {"name": tools[0], "arguments": json.dumps({"name": "Vela"})}}]}
    answers = [message["content"] for message in body["messages"] if message["role"] == "tool"]
    return {"content": f"Found: {answers[-1] if answers else 'nothing'}"}


@dataclass
class StandInModel:
    reply: Reply = calls_first_tool
    status: int = 200
    requests: list[dict[str, Any]] = field(default_factory=list)
    headers: list[dict[str, str]] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.headers.append(dict(request.headers))
        self.addresses.append(str(request.url))
        if request.url.path.endswith("/models"):
            listed = [{"id": "openai/b-model", "object": "model"}, {"id": "openai/a-model", "object": "model"}]
            return httpx.Response(200, json={"object": "list", "data": listed})
        if request.url.path.endswith("/images/generations"):
            body = json.loads(request.content)
            self.requests.append(body)
            return httpx.Response(self.status, json={"created": 1, "data": [{"b64_json": PICTURE}]} if self.status == 200 else {"error": {"message": "no"}})
        body = json.loads(request.content)
        self.requests.append(body)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": {"message": "refused", "type": "invalid_request_error"}})
        message = self.reply(body)
        finish = "tool_calls" if "tool_calls" in message else "stop"
        stream = chunk(body["model"], {"role": "assistant", **message}, None) + chunk(body["model"], {}, finish) + "data: [DONE]\n\n"
        return httpx.Response(200, content=stream.encode(), headers={"content-type": "text/event-stream"})


PICTURE = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAFklEQVR42mO4ICBAEmIY1TCqYfhqAABYoPABnlzdOQAAAABJRU5ErkJggg=="
