from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from aerona.services.statistics import EpochStatistics
from tests.api.conftest import ApiWorld
from tests.library_support import universe_headers


def foreign(api: ApiWorld, base_url: str) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=api.app), base_url=base_url, headers=universe_headers(api.universe_id))


async def test_only_localhost_hosts_are_served(api: ApiWorld) -> None:
    async with foreign(api, "http://evil.example") as client:
        response = await client.get("/api/health")
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_cross_site_writes_are_refused(api: ApiWorld) -> None:
    hostile = await api.http.patch("/api/creator", json={"title": "x"}, headers={"origin": "http://evil.example"})
    assert hostile.status_code == 403
    null_origin = await api.http.patch("/api/creator", json={"title": "x"}, headers={"origin": "null"})
    assert null_origin.status_code == 403
    cross_site = await api.http.patch("/api/creator", json={"title": "x"}, headers={"sec-fetch-site": "cross-site"})
    assert cross_site.status_code == 403
    same = await api.http.patch("/api/creator", json={"title": "Warden"}, headers={"origin": "http://localhost"})
    assert same.status_code == 200
    form = await api.http.patch("/api/creator", content=b"title=x", headers={"content-type": "application/x-www-form-urlencoded"})
    assert form.status_code == 415


async def test_large_bodies_are_refused(api: ApiWorld) -> None:
    response = await api.http.post("/api/notifications", content=b"{" + b" " * 3_000_000 + b"}", headers={"content-type": "application/json"})
    assert response.status_code == 413
    assert response.json()["code"] == "too_large"


async def test_unknown_endpoints_and_crashes_are_structured(api: ApiWorld, monkeypatch: pytest.MonkeyPatch) -> None:
    unknown = await api.http.get("/api/nowhere")
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "not_found"

    async def broken(*_args: object) -> list[EpochStatistics]:
        raise RuntimeError("secret detail at /Users/someone/aerona/data")

    monkeypatch.setattr("aerona.api.routers.epochs.series", broken)
    transport = ASGITransport(app=api.app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://localhost", headers=universe_headers(api.universe_id)) as client:
        crashed = await client.get("/api/stats/epochs")
    assert crashed.status_code == 500
    body = crashed.json()
    assert body["code"] == "internal"
    assert body["correlation_id"] in body["error"]
    assert "secret" not in body["error"]
    assert crashed.headers["x-correlation-id"] == body["correlation_id"]


VITE_CONFIG = Path(__file__).resolve().parents[3] / "frontend" / "vite.config.ts"


@pytest.mark.parametrize("port", [5173, 5192, 5200, 6123])
async def test_a_dev_server_on_any_port_writes_through_its_proxy(api: ApiWorld, port: int) -> None:
    async with foreign(api, f"http://localhost:{port}") as client:
        proxied = await client.patch("/api/creator", json={"title": "Warden"}, headers={"origin": f"http://localhost:{port}", "sec-fetch-site": "same-origin"})
    assert proxied.status_code == 200
    assert "changeOrigin: false" in VITE_CONFIG.read_text(encoding="utf-8")


def test_each_dev_server_keeps_its_own_dependency_cache_and_may_read_the_real_modules() -> None:
    config = VITE_CONFIG.read_text(encoding="utf-8")
    assert "cacheDir: path.resolve(ROOT, '.vite-cache', SERVER_KEY)" in config
    assert "realpathSync(path.resolve(ROOT, 'node_modules'))" in config
