import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from aerona_image_worker.app import create_app
from aerona_image_worker.domain.enums import BackendName, Isolation
from aerona_image_worker.settings import Settings

ClientFactory = Callable[..., AbstractAsyncContextManager[AsyncClient]]


def fake_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "backend": BackendName.FAKE,
        "isolation": Isolation.INLINE,
        "load_timeout_seconds": 5.0,
        "image_timeout_seconds": 5.0,
        "idle_unload_seconds": 0.0,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def worker_client() -> ClientFactory:
    @asynccontextmanager
    async def build(**overrides: Any) -> AsyncIterator[AsyncClient]:
        app = create_app(fake_settings(**overrides))
        async with LifespanManager(app) as manager:
            transport = ASGITransport(app=manager.app)
            async with AsyncClient(transport=transport, base_url="http://worker") as client:
                yield client

    return build


def job_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"prompt": "a lighthouse on a cliff", "width": 256, "height": 256, "steps": 3, "seed": 7, "priority": "manual"}
    body.update(overrides)
    return body


def parse_sse(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        data = [line.removeprefix("data:").strip() for line in block.split("\n") if line.startswith("data:")]
        if data:
            events.append(json.loads("\n".join(data)))
    return events


async def read_events(client: AsyncClient, job_id: str, last_event_id: int | None = None) -> list[dict[str, Any]]:
    headers = {"last-event-id": str(last_event_id)} if last_event_id is not None else {}
    response = await client.get(f"/jobs/{job_id}/events", headers=headers)
    assert response.status_code == 200
    return parse_sse(response.text)


async def eventually(check: Callable[[], Awaitable[bool]], attempts: int = 200, pause: float = 0.01) -> None:
    for _attempt in range(attempts):
        if await check():
            return
        await asyncio.sleep(pause)
    raise AssertionError("condition was not reached in time")
