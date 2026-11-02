import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.api import SAFE_METHODS
from aerona.constants.http import API_PREFIX, HEALTH_PATH
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.rules.registry import Rules
from aerona.services.container import Services

DISCOVERY_END_PATH = "/api/discovery/end"
HEALTH_PREFIX = f"{API_PREFIX}{HEALTH_PATH}"


def get_services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(get_services)]


async def guard_writes(request: Request, services: ServicesDep) -> None:
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
