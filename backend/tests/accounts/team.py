from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from aerona.constants.accounts import WORKSPACE_HEADER
from aerona.main import create_app
from aerona.services.accounts.service import AccountService
from aerona.settings import Settings
from tests.agents.world import seed_agent_world
from tests.library_support import accounts_of, opened_services, sign_in_owner, sole_universe, universe_headers

BASE_URL = "http://localhost"
NEW_PASSWORD = "a brand new evening walk"


@dataclass
class Team:
    app: FastAPI
    owner: AsyncClient
    universe_id: str
    workspace_id: int
    clients: list[AsyncClient]

    @property
    def accounts(self) -> AccountService:
        return accounts_of(self.app)

    def client(self, **headers: str) -> AsyncClient:
        made = AsyncClient(transport=ASGITransport(app=self.app), base_url=BASE_URL, headers=headers)
        self.clients.append(made)
        return made

    async def sign_in(self, login: str, password: str) -> AsyncClient:
        made = self.client(**universe_headers(self.universe_id))
        response = await made.post("/api/auth/sign-in", json={"login": login, "password": password})
        assert response.status_code == 200, response.text
        return made

    async def member(self, username: str, role: str, workspace_id: int | None = None) -> tuple[AsyncClient, dict[str, Any]]:
        workspace = workspace_id or self.workspace_id
        added = await self.owner.post(
            f"/api/workspaces/{workspace}/members",
            json={"username": username, "email": f"{username}@example.test", "display_name": username.title(), "role": role},
        )
        assert added.status_code == 201, added.text
        body = added.json()
        made = await self.sign_in(username, body["temporary_password"])
        changed = await made.post("/api/auth/password", json={"current": body["temporary_password"], "new": NEW_PASSWORD})
        assert changed.status_code == 200, changed.text
        made.headers[WORKSPACE_HEADER] = str(workspace)
        return made, body["member"]


@asynccontextmanager
async def team_of(settings: Settings) -> AsyncIterator[Team]:
    app = create_app(settings)
    async with LifespanManager(app, startup_timeout=120, shutdown_timeout=120):
        owner = AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL)
        await sign_in_owner(app, owner)
        universe = await sole_universe(app)
        services = await opened_services(app, universe)
        async with services.database.write() as session:
            await seed_agent_world(session, services.rules.current)
        owner.headers.update(universe_headers(universe))
        team = Team(app, owner, universe, int(owner.headers[WORKSPACE_HEADER]), [owner])
        try:
            yield team
        finally:
            for client in team.clients:
                await client.aclose()
