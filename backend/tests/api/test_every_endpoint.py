import re
import shutil
import tempfile
from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Any

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from aerona.constants.paths import DATABASE_FILENAME
from aerona.main import create_app
from aerona.prompts import PromptId
from aerona.settings import Settings
from tests.services.player.every_lever import kind_of, pick

PARAM = re.compile(r"\{(\w+)(?::path)?\}")
STREAMS = frozenset({"/api/events/stream", "/api/events"})
FIXED: Mapping[str, Any] = {
    "epoch": 1,
    "file_name": "missing.png",
    "job_id": "missing",
    "key": "missing",
    "kind": "missing",
    "prompt_id": next(iter(PromptId)).value,
}
SECOND = frozenset({"other_id"})
NAMED_TABLES: Mapping[str, str] = {"collection_id": "incident_collection_id"}


def api_paths() -> dict[str, dict[str, Any]]:
    settings = Settings(data_dir=Path(tempfile.mkdtemp()) / "data", llm_enabled=False, image_worker_url="")
    paths: dict[str, dict[str, Any]] = create_app(settings).openapi()["paths"]
    return paths


API_PATHS = api_paths()
GET_PATHS = sorted(path for path, methods in API_PATHS.items() if "get" in methods and path.startswith("/api") and path not in STREAMS)


def mismatched_path_params(paths: Mapping[str, Mapping[str, Any]]) -> list[str]:
    found: list[str] = []
    for path, methods in paths.items():
        wanted = set(PARAM.findall(path))
        for method, operation in methods.items():
            declared = {param["name"] for param in operation.get("parameters", []) if param.get("in") == "path"}
            if declared != wanted:
                found.append(f"{method.upper()} {path}: declares {sorted(declared)}")
    return found


def test_every_route_declares_the_path_params_of_its_template() -> None:
    assert mismatched_path_params(API_PATHS) == []


def test_a_shared_path_default_is_caught() -> None:
    shared = {"/api/things/{thing_id}": {"get": {"parameters": [{"name": "node_id", "in": "path"}]}}}
    assert mismatched_path_params(shared) == ["GET /api/things/{thing_id}: declares ['node_id']"]


@pytest.fixture
async def served(lever_template: Path, tmp_path: Path) -> AsyncIterator[tuple[AsyncClient, Any]]:
    settings = Settings(data_dir=tmp_path / "data", llm_enabled=False, image_worker_url="")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(lever_template, settings.data_dir / DATABASE_FILENAME)
    app = create_app(settings)
    async with (
        LifespanManager(app, startup_timeout=120, shutdown_timeout=120) as manager,
        AsyncClient(transport=ASGITransport(app=manager.app), base_url="http://localhost") as http,
    ):
        yield http, app.state.services


async def filled(services: Any, path: str) -> str:
    values: dict[str, Any] = {}
    async with services.database.read() as session:
        for name in PARAM.findall(path):
            if name in FIXED:
                values[name] = FIXED[name]
                continue
            found = await pick(session, kind_of("mortal_id" if name in SECOND else NAMED_TABLES.get(name, name)), 1 if name in SECOND else 0)
            values[name] = found if found is not None else 0
    return PARAM.sub(lambda match: str(values[match.group(1)]), path)


def repeated_refs(value: Any, where: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.extend(repeated_refs(item, f"{where}.{key}"))
    elif isinstance(value, list):
        refs = [(item["kind"], item["id"]) for item in value if isinstance(item, dict) and set(item) == {"kind", "id", "name"}]
        if len(refs) == len(value) and len(set(refs)) < len(refs):
            found.append(where)
        for item in value:
            found.extend(repeated_refs(item, where))
    return found


def test_a_list_naming_one_node_twice_is_caught() -> None:
    ref = {"kind": "entity", "id": 7, "name": "Vel"}
    assert repeated_refs({"dreams": [{"content": [ref, ref]}], "fine": [ref]}) == [".dreams.content"]


async def test_every_read_endpoint_answers_without_a_server_error(served: tuple[AsyncClient, Any]) -> None:
    http, services = served
    broken: list[str] = []
    for path in GET_PATHS:
        url = await filled(services, path)
        response = await http.get(url)
        if response.status_code >= 500:
            broken.append(f"{url}: {response.status_code} {response.text[:300]}")
        elif response.status_code == 200 and response.headers.get("content-type", "").startswith("application/json"):
            broken.extend(f"{url}: names one node twice in {where}" for where in repeated_refs(response.json()))
    assert broken == []
    assert len(GET_PATHS) > 200
