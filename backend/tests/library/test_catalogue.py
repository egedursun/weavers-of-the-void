from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from aerona.constants.app import APP_VERSION
from aerona.db.library.tables import LibraryBase
from aerona.domain.enums.library import LibraryEventKind, UniverseOrigin, UniverseSort, UniverseStatus
from aerona.paths import ProcessPaths
from aerona.services.library.catalogue import Catalogue, NewUniverse, UniverseEdit, UniverseQuery


def made(name: str, *, tags: tuple[str, ...] = ()) -> NewUniverse:
    return NewUniverse(name=name, origin=UniverseOrigin.CREATED, media_prefix="", app_version=APP_VERSION, tags=tags)


async def test_the_library_migrations_reach_the_models(tmp_path: Path) -> None:
    catalogue = Catalogue(ProcessPaths(tmp_path))
    await catalogue.open()
    await catalogue.close()
    engine = create_engine(f"sqlite:///{tmp_path / 'library.db'}")
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), LibraryBase.metadata)
    engine.dispose()
    assert differences == []


async def test_edits_names_tags_and_paging(tmp_path: Path) -> None:
    catalogue = Catalogue(ProcessPaths(tmp_path))
    await catalogue.add("aaaaaaaaaaa1", made("Shelf", tags=("Long", "long", " ", "short")))
    await catalogue.add("aaaaaaaaaaa2", made("Other"))
    assert (await catalogue.require("aaaaaaaaaaa1")).tags == ("Long", "short")
    assert await catalogue.free_name("shelf") == "shelf (2)"
    assert await catalogue.free_name("Shelf", keep="aaaaaaaaaaa1") == "Shelf"
    renamed = await catalogue.edit("aaaaaaaaaaa2", UniverseEdit(name="  Third   shelf ", pinned=True))
    assert renamed.name == "Third shelf"
    await catalogue.set_status("aaaaaaaaaaa1", UniverseStatus.ARCHIVED)
    active = await catalogue.page(UniverseQuery())
    assert [record.id for record in active.universes] == ["aaaaaaaaaaa2"]
    assert active.statuses == {UniverseStatus.ACTIVE: 1, UniverseStatus.ARCHIVED: 1}
    tagged = await catalogue.page(UniverseQuery(status=None, tag="long", sort=UniverseSort.NAME))
    assert [record.id for record in tagged.universes] == ["aaaaaaaaaaa1"]
    found = await catalogue.page(UniverseQuery(status=None, text="third"))
    assert found.total == 1
    events, total = await catalogue.events(universe_id="aaaaaaaaaaa2")
    assert total == 1
    assert events[0].kind is LibraryEventKind.RENAMED
    assert events[0].detail == "Other"
    await catalogue.close()
