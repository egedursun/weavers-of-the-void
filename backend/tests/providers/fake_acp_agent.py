import json
import os
import sys
import threading

import httpx

MODE = os.environ.get("FAKE_MODE", "tool")
LOG = os.environ.get("FAKE_LOG", "")
ANSWER = json.loads(os.environ.get("FAKE_ANSWER", "{}"))
HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}
state: dict[str, object] = {"next": 1000, "cancelled": False}
waiting: dict[int, dict[str, object]] = {}
ready = threading.Condition()


def log(entry: dict[str, object]) -> None:
    if LOG:
        with open(LOG, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")


def send(message: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def update(session_id: str, body: dict[str, object]) -> None:
    send({"jsonrpc": "2.0", "method": "session/update", "params": {"sessionId": session_id, "update": body}})


def ask(method: str, params: dict[str, object]) -> dict[str, object]:
    number = int(state["next"])
    state["next"] = number + 1
    send({"jsonrpc": "2.0", "id": number, "method": method, "params": params})
    with ready:
        while number not in waiting:
            ready.wait()
        return waiting.pop(number)


def mcp(url: str, method: str, params: dict[str, object]) -> dict[str, object]:
    reply = httpx.post(url, headers=HEADERS, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=30)
    reply.raise_for_status()
    found = reply.json()
    log({"mcp": method, "result": found.get("result")})
    return found.get("result") or {}


def call(session_id: str, url: str, name: str, arguments: dict[str, object], number: int) -> str:
    update(session_id, {"sessionUpdate": "tool_call", "toolCallId": f"tc{number}", "title": f"aerona-{name}", "status": "pending", "rawInput": arguments})
    shown = {} if MODE == "untitled" else {"title": name}
    decision = ask(
        "session/request_permission",
        {
            "sessionId": session_id,
            "toolCall": {"toolCallId": f"tc{number}", **shown, "rawInput": arguments},
            "options": [{"optionId": "yes", "kind": "allow_once", "name": "Allow"}, {"optionId": "no", "kind": "reject_once", "name": "Reject"}],
        },
    )
    outcome = (decision.get("result") or {}).get("outcome") or {}
    log({"permission": name, "outcome": outcome})
    if outcome.get("optionId") != "yes":
        return "rejected"
    result = mcp(url, "tools/call", {"name": name, "arguments": arguments})
    update(session_id, {"sessionUpdate": "tool_call_update", "toolCallId": f"tc{number}", "status": "completed"})
    return " ".join(part.get("text", "") for part in result.get("content", []))


def prompt(message: dict[str, object]) -> None:
    params = message["params"]
    session_id = str(params["sessionId"])
    url = str(state["url"])
    log({"prompt": params["prompt"]})
    mcp(url, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "fake", "version": "1"}})
    tools = [tool["name"] for tool in mcp(url, "tools/list", {}).get("tools", [])]
    update(session_id, {"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": "Info: some tools are switched off"}})
    update(session_id, {"sessionUpdate": "agent_message_chunk", "messageId": "m1", "content": {"type": "text", "text": "Let me look."}})
    stop = "end_turn"
    if MODE in {"tool", "untitled"}:
        result = call(session_id, url, tools[0], {"name": "Vela"}, 1)
        update(session_id, {"sessionUpdate": "agent_message_chunk", "messageId": "m2", "content": {"type": "text", "text": f"Found: {result}"}})
    elif MODE == "forbidden":
        result = call(session_id, url, "run_shell_command", {"command": "ls"}, 1)
        update(session_id, {"sessionUpdate": "agent_message_chunk", "messageId": "m2", "content": {"type": "text", "text": result}})
    elif MODE == "answer":
        call(session_id, url, "answer", ANSWER, 1)
    elif MODE == "loop":
        number = 1
        while not state["cancelled"]:
            call(session_id, url, tools[0], {"name": f"Star {number}"}, number)
            number += 1
        stop = "cancelled"
    elif MODE == "quota":
        send({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32000, "message": "rate limit reached, try again later"}})
        return
    send({"jsonrpc": "2.0", "id": message["id"], "result": {"stopReason": stop}})


def guarded(message: dict[str, object]) -> None:
    try:
        prompt(message)
    except Exception as error:
        send({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32603, "message": f"fake agent failed: {error}"}})


def handle(message: dict[str, object]) -> None:
    method = message.get("method")
    log({"method": method, "params": message.get("params")})
    if method == "initialize":
        capabilities = {"promptCapabilities": {"image": True}, "mcpCapabilities": {"http": True}, "sessionCapabilities": {"systemPrompt": {}, "close": {}}}
        send({"jsonrpc": "2.0", "id": message["id"], "result": {"protocolVersion": 1, "agentCapabilities": capabilities, "authMethods": []}})
    elif method == "authenticate":
        if MODE == "refuse":
            send({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32000, "message": "Authentication required"}})
        else:
            send({"jsonrpc": "2.0", "id": message["id"], "result": {}})
    elif method == "session/new":
        state["url"] = message["params"]["mcpServers"][0]["url"] if message["params"]["mcpServers"] else ""
        options = [{"id": "model", "category": "model", "type": "select", "currentValue": "m1", "options": [{"value": "m1"}, {"value": "m2"}]}]
        modes = {"currentModeId": "auto", "availableModes": [{"id": "auto", "name": "Auto"}, {"id": "careful", "name": "Careful"}]}
        send({"jsonrpc": "2.0", "id": message["id"], "result": {"sessionId": "s1", "configOptions": options, "modes": modes}})
    elif method in {"session/set_config_option", "session/close", "session/set_mode"}:
        send({"jsonrpc": "2.0", "id": message["id"], "result": {}})
    elif method == "session/prompt":
        threading.Thread(target=guarded, args=(message,), daemon=True).start()
    elif method == "session/cancel":
        state["cancelled"] = True


def main() -> None:
    for line in sys.stdin:
        message = json.loads(line)
        if "method" not in message and "id" in message:
            with ready:
                waiting[int(message["id"])] = message
                ready.notify_all()
        else:
            handle(message)


if __name__ == "__main__":
    main()
