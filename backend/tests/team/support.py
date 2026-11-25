import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.job import JobKind
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.jobs.context import JobContext
from aerona.services.container import Services
from tests.accounts.team import Team
from tests.library_support import opened_services
from tests.polling import until

GUILD = "The Guild"


async def guild(team: Team) -> int:
    made = await team.owner.post("/api/workspaces", json={"name": GUILD})
    assert made.status_code == 201, made.text
    workspace_id = int(made.json()["id"])
    moved = await team.owner.post(f"/api/library/universes/{team.universe_id}/move", json={"workspace_id": workspace_id})
    assert moved.status_code == 200, moved.text
    team.owner.headers["X-Aerona-Workspace"] = str(workspace_id)
    return workspace_id


async def services_of(team: Team) -> Services:
    return await opened_services(team.app, team.universe_id)


async def a_mortal(team: Team) -> EntityRow:
    services = await services_of(team)
    async with services.database.read() as session:
        found = await session.scalar(
            select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
        )
    assert found is not None
    return found


@asynccontextmanager
async def an_age(services: Services) -> AsyncIterator[asyncio.Event]:
    release = asyncio.Event()

    async def hold(context: JobContext) -> dict[str, Any]:
        await release.wait()
        return {}

    await services.jobs.submit(JobKind.EPOCH, hold, exclusive_group=WORLD_GROUP)
    assert await until(lambda: services.jobs.busy_group(WORLD_GROUP) is not None)
    try:
        yield release
    finally:
        release.set()
        assert await until(lambda: services.jobs.busy_group(WORLD_GROUP) is None)


async def settled_act(client: AsyncClient, act_id: int) -> dict[str, Any]:
    found: dict[str, Any] = {}

    async def done() -> bool:
        items = (await client.get("/api/team/queue")).json()["items"]
        found.update(next(item for item in items if item["id"] == act_id))
        return bool(found["status"] != "queued")

    assert await until(done), f"queued act {act_id} never settled"
    return found


async def edit(client: AsyncClient, entity_id: int, body: dict[str, Any], **query: Any) -> Any:
    return await client.patch(f"/api/entities/{entity_id}", json=body, params=query)
