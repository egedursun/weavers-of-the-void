import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from starlette.types import ASGIApp

from aerona.agents.ports import LanguageModel
from aerona.domain.enums.job import TERMINAL_JOB_STATUSES, JobStatus
from aerona.main import create_app
from aerona.services.container import Services
from aerona.settings import Settings
from tests.agents.world import AgentWorld, seed_agent_world

STARTUP_SECONDS = 120

LOCAL_BASE_URL = "http://localhost"
JOB_POLL_SECONDS = 0.05
JOB_POLL_ATTEMPTS = 600


@dataclass
class ApiWorld:
    http: AsyncClient
    services: Services
    app: ASGIApp
    world: AgentWorld | None = None

    async def wait_job(self, job_id: str) -> dict[str, Any]:
        for _ in range(JOB_POLL_ATTEMPTS):
            response = await self.http.get(f"/api/jobs/{job_id}")
            body: dict[str, Any] = response.json()
            if JobStatus(body["status"]) in TERMINAL_JOB_STATUSES:
                return body
            await asyncio.sleep(JOB_POLL_SECONDS)
        raise AssertionError(f"job {job_id} did not finish")

    async def settle(self) -> None:
        for _ in range(JOB_POLL_ATTEMPTS):
            if not self.services.application.background and not self.services.jobs.running_count:
                return
            await asyncio.sleep(JOB_POLL_SECONDS)


async def open_api(settings: Settings, *, model: LanguageModel | None = None, seeded: bool) -> AsyncIterator[ApiWorld]:
    app = create_app(settings, model=model)
    async with LifespanManager(app, startup_timeout=STARTUP_SECONDS, shutdown_timeout=STARTUP_SECONDS) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url=LOCAL_BASE_URL) as http:
            services: Services = app.state.services
            api = ApiWorld(http=http, services=services, app=manager.app)
            await api.settle()
            if seeded:
                async with services.database.write() as session:
                    api.world = await seed_agent_world(session, services.rules.current)
            yield api
            await api.settle()


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    async for api in open_api(settings, seeded=False):
        yield api.http


@pytest.fixture
async def empty_api(settings: Settings) -> AsyncIterator[ApiWorld]:
    async for api in open_api(settings, seeded=False):
        yield api


@pytest.fixture
async def api(settings: Settings) -> AsyncIterator[ApiWorld]:
    async for opened in open_api(settings, seeded=True):
        yield opened


def seeded(api: ApiWorld) -> AgentWorld:
    assert api.world is not None
    return api.world
