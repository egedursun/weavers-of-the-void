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
from tests.library_support import opened_services, sign_in_owner, sole_universe, universe_headers
from tests.polling import until

STARTUP_SECONDS = 120

LOCAL_BASE_URL = "http://localhost"
JOB_POLL_SECONDS = 0.05


@dataclass
class ApiWorld:
    http: AsyncClient
    services: Services
    app: ASGIApp
    universe_id: str
    world: AgentWorld | None = None

    async def wait_job(self, job_id: str) -> dict[str, Any]:
        bodies: list[dict[str, Any]] = []

        async def done() -> bool:
            bodies.append((await self.http.get(f"/api/jobs/{job_id}")).json())
            return JobStatus(bodies[-1]["status"]) in TERMINAL_JOB_STATUSES

        if not await until(done, step=JOB_POLL_SECONDS):
            raise AssertionError(f"job {job_id} did not finish")
        return bodies[-1]

    async def settle(self) -> None:
        await until(lambda: not self.services.application.background and not self.services.jobs.running_count, step=JOB_POLL_SECONDS)


async def open_api(settings: Settings, *, model: LanguageModel | None = None, seeded: bool) -> AsyncIterator[ApiWorld]:
    app = create_app(settings, model=model)
    async with LifespanManager(app, startup_timeout=STARTUP_SECONDS, shutdown_timeout=STARTUP_SECONDS) as manager:
        transport = ASGITransport(app=manager.app)
        universe = await sole_universe(app)
        services = await opened_services(app, universe)
        async with AsyncClient(transport=transport, base_url=LOCAL_BASE_URL, headers=universe_headers(universe)) as http:
            await sign_in_owner(app, http)
            api = ApiWorld(http=http, services=services, app=manager.app, universe_id=universe)
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


async def fund_creator(api: ApiWorld) -> None:
    async with api.services.database.write() as session:
        seeded(api).core.creator.essence = 100000
        await session.merge(seeded(api).core.creator)
