import re
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from aerona.services.books.mapsvg import MapPicture
from aerona.services.books.render import CodexLinks, ScreenLinks
from aerona.settings import Settings
from tests.api.conftest import ApiWorld, open_api, seeded
from tests.library.shelf import png

TEMPLATES = Path(__file__).resolve().parents[2] / "src" / "aerona" / "services" / "books" / "templates"
API_URL = re.compile(r"/api/[^\"'\s)<>\\]*")
RAW_API = re.compile(r"""["'(]/api/""")
SCOPED_CALL = re.compile(r"links\.api\([^)]*\)")


@pytest.fixture
async def world(settings: Settings) -> AsyncIterator[ApiWorld]:
    async for opened in open_api(settings, seeded=True):
        yield opened


def unscoped(html: str, universe: str) -> list[str]:
    return [url for url in API_URL.findall(html) if f"universe={universe}" not in url]


async def test_every_api_url_in_the_book_names_its_universe(world: ApiWorld) -> None:
    town = seeded(world).core.extra["town"].id
    await world.http.post("/api/images", params={"node_id": town}, content=png(), headers={"content-type": "image/png"})
    whole = await world.http.get("/api/book")
    assert whole.status_code == 200
    assert API_URL.findall(whole.text)
    assert unscoped(whole.text, world.universe_id) == []
    entry = await world.http.get("/api/book", params={"entity_id": town})
    assert entry.status_code == 200
    assert unscoped(entry.text, world.universe_id) == []
    assert "?entity_id=" not in entry.text or f"universe={world.universe_id}" in entry.text
    assert f'class="back" href="/overview?universe={world.universe_id}"' in whole.text


def test_screen_and_codex_links_carry_the_universe() -> None:
    picture = cast(MapPicture, SimpleNamespace(world_id=3, signature="abc"))
    screen = ScreenLinks(universe="abcdefghijkl")
    for url in (
        screen.media("a.png", "article"),
        screen.terrain(picture),
        screen.font("f.woff2"),
        screen.logo(),
        screen.api("/api/book"),
        screen.entry("son", 4),
    ):
        assert "universe=abcdefghijkl" in url
    codex = CodexLinks(base="http://localhost/", universe="abcdefghijkl")
    assert codex.media("a.png").endswith("&universe=abcdefghijkl")
    assert ScreenLinks().api("/api/book") == "/api/book"


def test_no_template_writes_a_raw_api_url() -> None:
    found = [
        f"{path.name}: {line.strip()[:120]}"
        for path in sorted(TEMPLATES.rglob("*.j2"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if RAW_API.search(SCOPED_CALL.sub("", line))
    ]
    assert found == []
