import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.api import SAFE_METHODS
from aerona.constants.http import API_PREFIX, HEALTH_PATH, LIBRARY_PATH
from aerona.constants.library import UNIVERSE_HEADER, UNIVERSE_QUERY
from aerona.core.errors import UniverseRequiredError
from aerona.core.universe_scope import enter_universe
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.rules.registry import Rules
from aerona.services.container import Services
from aerona.services.library.hub import CHOOSE_UNIVERSE, UniverseHub
from aerona.services.library.runtime import UniverseRuntime

DISCOVERY_END_PATH = "/api/discovery/end"
HEALTH_PREFIX = f"{API_PREFIX}{HEALTH_PATH}"
LIBRARY_PREFIX = f"{API_PREFIX}{LIBRARY_PATH}"


def get_hub(request: Request) -> UniverseHub:
    hub: UniverseHub = request.app.state.hub
    return hub


HubDep = Annotated[UniverseHub, Depends(get_hub)]


def universe_named(request: Request) -> str | None:
    named = request.headers.get(UNIVERSE_HEADER) or request.query_params.get(UNIVERSE_QUERY)
    return named.strip() if named and named.strip() else None


def universe_free(path: str) -> bool:
    return path == LIBRARY_PREFIX or path.startswith(f"{LIBRARY_PREFIX}/")


async def bound_runtime(request: Request, hub: HubDep) -> AsyncIterator[UniverseRuntime | None]:
    universe_id = universe_named(request)
    if universe_id is None or universe_free(request.url.path):
        yield None
        return
    runtime = await hub.acquire(universe_id)
    enter_universe(universe_id)
    try:
        yield runtime
    finally:
        hub.release(runtime)


RuntimeDep = Annotated[UniverseRuntime | None, Depends(bound_runtime)]


async def get_services(runtime: RuntimeDep) -> Services:
    if runtime is None:
        raise UniverseRequiredError(CHOOSE_UNIVERSE)
    return runtime.services


ServicesDep = Annotated[Services, Depends(get_services)]


async def guard_writes(request: Request, runtime: RuntimeDep) -> None:
    if runtime is None:
        return
    services = runtime.services
    await repairs_finished(request, services)
    if request.method.upper() in SAFE_METHODS or request.url.path == DISCOVERY_END_PATH:
        return
    services.application.discovery.ensure_writable()


async def repairs_finished(request: Request, services: Services) -> None:
    ready = services.application.repairs_ready
    if ready.is_set() or request.url.path.startswith(HEALTH_PREFIX):
        return
    wait = services.rules.current.server.repair_wait_seconds
    if wait:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(ready.wait(), timeout=wait)


@asynccontextmanager
async def reader(services: Services) -> AsyncIterator[AsyncSession]:
    discovery = services.application.discovery
    if discovery.active:
        async with discovery.guest_session() as session:
            yield session
        return
    async with services.database.read() as session:
        yield session


async def world_rules(services: Services, session: AsyncSession) -> Rules:
    cosmos = await CosmosRepository(session).get()
    if cosmos is None or not cosmos.rules_snapshot:
        return services.rules.current
    return rules_from_snapshot(cosmos.rules_snapshot)
