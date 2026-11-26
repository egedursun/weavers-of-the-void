from datetime import UTC, datetime

from sqlalchemy import select

from aerona.db.tables.cosmos import CosmosRow
from aerona.domain.enums.library import UniverseOrigin
from aerona.services.library.manifest import UniverseManifest, write_manifest
from tests.api.conftest import ApiWorld

UNIVERSE_ID = "rakhesis0001"
UNIVERSE_NAME = "Rakhesis"


def shelved(api: ApiWorld) -> None:
    settings = api.services.settings.model_copy(update={"universe_id": UNIVERSE_ID})
    folder = settings.process.universe(UNIVERSE_ID)
    folder.root.mkdir(parents=True, exist_ok=True)
    manifest = UniverseManifest(
        id=UNIVERSE_ID,
        name=UNIVERSE_NAME,
        summary="",
        notes="",
        tags=(),
        origin=UniverseOrigin.CREATED,
        origin_note="",
        media_prefix="",
        created_at=datetime.now(UTC),
        schema_revision="",
        app_version="",
        epoch=0,
        year=0,
    )
    write_manifest(folder.manifest, manifest)
    api.services.settings = settings


async def test_the_book_and_the_codex_carry_the_universe_name_not_the_first_world(api: ApiWorld) -> None:
    async with api.services.database.read() as session:
        world_name = (await session.scalars(select(CosmosRow.name))).one()
    assert world_name != UNIVERSE_NAME
    former = api.services.settings
    shelved(api)
    try:
        codex = await api.http.get("/api/codex.md")
        book = await api.http.get("/api/book")
    finally:
        api.services.settings = former
    assert f'filename="{UNIVERSE_NAME}' in codex.headers["content-disposition"]
    assert codex.text.lstrip().startswith(f"# {UNIVERSE_NAME}") or f"\n# {UNIVERSE_NAME}\n" in codex.text
    assert f"The book of {UNIVERSE_NAME}," in codex.text
    assert f"<h1>{UNIVERSE_NAME}</h1>" in book.text
