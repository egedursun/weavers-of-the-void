from pathlib import Path

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from aerona.main import create_app
from aerona.settings import Settings

INDEX = "<!doctype html><title>Aerona</title>"
STARTUP_SECONDS = 120


async def test_built_frontend_is_served_with_spa_fallback(tmp_path: Path) -> None:
    static = tmp_path / "web"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text(INDEX, encoding="utf-8")
    (static / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    settings = Settings(data_dir=tmp_path / "data", llm_enabled=False, image_worker_url="", static_dir=static)
    app = create_app(settings)
    async with (
        LifespanManager(app, startup_timeout=STARTUP_SECONDS, shutdown_timeout=STARTUP_SECONDS) as manager,
        AsyncClient(transport=ASGITransport(app=manager.app), base_url="http://localhost") as http,
    ):
        assert (await http.get("/")).text == INDEX
        assert (await http.get("/pantheon/sons")).text == INDEX
        assert (await http.get("/assets/app.js")).status_code == 200
        assert (await http.get("/../settings.py")).text == INDEX
        unknown = await http.get("/api/nothing-here")
        assert unknown.status_code == 404
        assert unknown.json()["code"] == "not_found"
