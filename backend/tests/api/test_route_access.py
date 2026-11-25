import re
from collections.abc import AsyncIterator

import pytest
from fastapi.routing import APIRoute
from httpx import AsyncClient

from aerona.api.access import Access, AccessKind, declared
from aerona.api.app import api_routes
from aerona.constants.accounts import WORKSPACE_HEADER
from aerona.services.accounts.permissions import VIEWER_DEFAULTS, lever_permission
from aerona.settings import Settings
from tests.accounts.team import Team, team_of

PARAMETER = re.compile(r"\{([a-z_]+)(?::[a-z]+)?\}")
SKIPPED_METHODS = frozenset({"HEAD", "OPTIONS"})
NUMBER = "1"
WORD = "aaaaaaaaaaaa"
UNSUPPORTED = 415


@pytest.fixture
async def team(settings: Settings) -> AsyncIterator[Team]:
    async with team_of(settings) as made:
        made_workspace = await made.owner.post("/api/workspaces", json={"name": "The Guild"})
        workspace_id = int(made_workspace.json()["id"])
        await made.owner.post(f"/api/library/universes/{made.universe_id}/move", json={"workspace_id": workspace_id})
        made.owner.headers[WORKSPACE_HEADER] = str(workspace_id)
        made.workspace_id = workspace_id
        yield made


def filled(path: str, team: Team) -> str:
    def value(found: re.Match[str]) -> str:
        name = found.group(1)
        if name == "universe_id":
            return team.universe_id
        if name == "workspace_id":
            return str(team.workspace_id)
        if name.endswith("_id") or name in {"epoch", "ordinal", "version"}:
            return NUMBER
        return WORD

    return "/api" + PARAMETER.sub(value, path) if not path.startswith("/api") else PARAMETER.sub(value, path)


def viewer_refused(access: Access) -> bool:
    if access.kind is AccessKind.SERVER_ADMIN:
        return True
    if access.kind is AccessKind.WORKSPACE:
        return access.workspace_role is not None and access.workspace_role.value != "viewer"
    if access.kind is AccessKind.UNIVERSE:
        return access.universe_admin or (access.permission is not None and access.permission not in VIEWER_DEFAULTS)
    return False


def checked_routes() -> list[tuple[str, APIRoute, Access]]:
    found = []
    for route in api_routes():
        for method in sorted(route.methods or ()):
            access = declared(route, method, lever_permission)
            assert access is not None, f"{method} {route.path}"
            if method in SKIPPED_METHODS or access.kind is AccessKind.OPEN:
                continue
            found.append((method, route, access))
    return found


async def answer(client: AsyncClient, method: str, path: str) -> int:
    if method not in {"POST", "PUT", "PATCH"}:
        return (await client.request(method, path)).status_code
    status = (await client.request(method, path, json={})).status_code
    if status == UNSUPPORTED:
        status = (await client.request(method, path, content=b"x", headers={"content-type": "application/octet-stream"})).status_code
    if status == UNSUPPORTED:
        status = (await client.request(method, path, files={"file": ("x.bin", b"x")})).status_code
    return status


async def test_every_declared_route_refuses_the_signed_out_and_the_viewer_without_its_permission(team: Team) -> None:
    viewer, _ = await team.member("vio", "viewer", team.workspace_id)
    stranger = team.client(**dict(viewer.headers))
    wrong: list[str] = []
    for method, route, access in checked_routes():
        path = filled(route.path, team)
        if await answer(stranger, method, path) != 401:
            wrong.append(f"signed out {method} {route.path}")
        if viewer_refused(access) and (status := await answer(viewer, method, path)) != 403:
            wrong.append(f"viewer {method} {route.path} answered {status}")
    assert wrong == []
