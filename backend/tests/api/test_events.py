import asyncio
import json
from typing import Any

from aerona.api.routers.events import stream_events
from aerona.constants.library import UNIVERSE_QUERY
from aerona.constants.timeouts import SSE_PING_SECONDS
from aerona.domain.enums.job import JobKind
from aerona.events.kinds import EventKind
from tests.api.conftest import ApiWorld


async def test_activity_log_returns_typed_events(api: ApiWorld) -> None:
    api.services.bus.publish(EventKind.SYSTEM_NOTE, {"text": "The salt sleeps."})
    events = (await api.http.get("/api/activity-log")).json()
    notes = [event for event in events if event["kind"] == "system.note"]
    assert notes[-1]["payload"]["text"] == "The salt sleeps."
    after = (await api.http.get("/api/activity-log", params={"after": notes[-1]["id"]})).json()
    assert all(event["id"] > notes[-1]["id"] for event in after)


async def test_malformed_events_are_left_out(api: ApiWorld) -> None:
    api.services.bus.publish(EventKind.LEDGER_UNDONE, {"entry": "wrong"})
    events = (await api.http.get("/api/activity-log")).json()
    assert all(event["kind"] != "ledger.undone" for event in events)


STREAM_WAIT_SECONDS = 5


async def read_stream(api: ApiWorld, *, query: str = "", headers: dict[str, str] | None = None, until: int, publish_after: int = 0) -> list[dict[str, Any]]:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/events",
        "raw_path": b"/api/events",
        "query_string": "&".join(part for part in (f"{UNIVERSE_QUERY}={api.universe_id}", query) if part).encode(),
        "headers": [
            (b"host", b"localhost"),
            (b"accept", b"text/event-stream"),
            (b"cookie", "; ".join(f"{name}={value}" for name, value in api.http.cookies.items()).encode()),
            *[(key.encode(), value.encode()) for key, value in (headers or {}).items()],
        ],
        "server": ("localhost", 80),
        "client": ("127.0.0.1", 1),
    }
    chunks: list[bytes] = []
    gate = asyncio.Event()
    ready = asyncio.Event()

    async def receive() -> dict[str, Any]:
        await gate.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))
            if len(parse_sse(b"".join(chunks))) >= until:
                ready.set()

    task = asyncio.create_task(api.app(scope, receive, send))
    try:
        async with asyncio.timeout(STREAM_WAIT_SECONDS):
            await ready.wait()
    finally:
        gate.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    return parse_sse(b"".join(chunks))


def parse_sse(raw: bytes) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for block in raw.decode().replace("\r\n", "\n").split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.split("\n"):
            if ":" in line and not line.startswith(":"):
                key, _, value = line.partition(":")
                fields[key] = value.strip()
        if "data" in fields:
            messages.append({"event": fields.get("event"), "id": fields.get("id"), "data": json.loads(fields["data"])})
    return messages


async def test_stream_opens_with_hello_carrying_the_busy_state(api: ApiWorld) -> None:
    messages = await read_stream(api, until=1)
    hello = messages[0]
    assert hello["event"] == "stream.hello"
    assert hello["data"]["kind"] == "stream.hello"
    assert hello["data"]["payload"]["busy"] is False
    assert hello["data"]["payload"]["last_event_id"] == api.services.bus.last_id
    assert hello["id"] is None


async def test_hello_reports_a_running_exclusive_job(api: ApiWorld) -> None:
    release = asyncio.Event()

    async def hold(context: Any) -> None:
        await release.wait()

    await api.services.jobs.submit(JobKind.CONTENT, hold, exclusive_group="test-group")
    try:
        messages = await read_stream(api, until=1)
    finally:
        release.set()
        await api.settle()
    payload = messages[0]["data"]["payload"]
    assert payload["busy"] is True
    assert payload["groups"] == ["test-group"]
    assert payload["running_jobs"] == 1


async def test_stream_delivers_live_events_with_ids(api: ApiWorld) -> None:
    async def publish_later() -> None:
        await asyncio.sleep(0.2)
        api.services.bus.publish(EventKind.SYSTEM_NOTE, {"text": "Live line."})

    publisher = asyncio.create_task(publish_later())
    messages = await read_stream(api, until=2)
    await publisher
    live = messages[1]
    assert live["event"] == "system.note"
    assert live["data"]["payload"]["text"] == "Live line."
    assert live["id"] == str(live["data"]["id"])


async def test_stream_resumes_from_last_event_id_header_and_after_query(api: ApiWorld) -> None:
    bus = api.services.bus
    first = bus.publish(EventKind.SYSTEM_NOTE, {"text": "one"})
    bus.publish(EventKind.SYSTEM_NOTE, {"text": "two"})
    bus.publish(EventKind.SYSTEM_NOTE, {"text": "three"})
    by_header = await read_stream(api, headers={"last-event-id": str(first.id)}, until=3)
    assert [item["data"]["payload"]["text"] for item in by_header[1:]] == ["two", "three"]
    by_query = await read_stream(api, query=f"after={first.id}", until=3)
    assert [item["data"]["payload"]["text"] for item in by_query[1:]] == ["two", "three"]
    header_wins = await read_stream(api, query="after=0", headers={"last-event-id": str(first.id + 1)}, until=2)
    assert [item["data"]["payload"]["text"] for item in header_wins[1:]] == ["three"]


async def test_stream_pings_every_keep_alive_interval(api: ApiWorld) -> None:
    response = await stream_events(api.services, None, None)
    assert response.ping_interval == SSE_PING_SECONDS == 20


async def test_transient_events_are_streamed_but_never_replayed(api: ApiWorld) -> None:
    bus = api.services.bus
    streamed = bus.publish(EventKind.AGENT_STREAM, {"actor_kind": "son", "actor_id": 1, "actor_name": "Velkar", "text": "salt", "chars": 4})
    kept = bus.publish(EventKind.SYSTEM_NOTE, {"text": "kept"})
    assert streamed.id < kept.id
    assert [item.id for item in bus.replay_after(0)][-1] == kept.id
    assert streamed.id not in [item.id for item in bus.replay_after(0)]
    log = (await api.http.get("/api/activity-log")).json()
    assert all(event["kind"] != "agent.stream" for event in log)
