import json
import shutil
from pathlib import Path

from aerona.domain.enums.library import LibraryEventKind, UniverseOrigin
from aerona.paths import ProcessPaths
from aerona.services.library.adoption import adopt_old_layout, mark_adoption, prepare_library
from aerona.services.library.catalogue import Catalogue

OWNED_FOLDERS = ("media", "backups", "exports", "forecasts", "discovery")


def old_layout(root: Path, schema_template: Path) -> None:
    root.mkdir(parents=True)
    shutil.copyfile(schema_template, root / "aerona.db")
    for folder in OWNED_FOLDERS:
        (root / folder).mkdir()
        (root / folder / "kept.txt").write_text(folder, encoding="utf-8")
    (root / "secondary-backup-target.json").write_text(json.dumps({"directory": None}), encoding="utf-8")
    (root / "unrelated.db").write_text("left alone", encoding="utf-8")


async def test_the_old_layout_becomes_the_first_universe_once(tmp_path: Path, schema_template: Path) -> None:
    root = tmp_path / "data"
    old_layout(root, schema_template)
    catalogue = Catalogue(ProcessPaths(root))
    adopted = await adopt_old_layout(catalogue)
    assert adopted is not None
    folder = root / "universes" / adopted
    assert (folder / "aerona.db").is_file()
    assert not (root / "aerona.db").exists()
    for name in OWNED_FOLDERS:
        assert (folder / name / "kept.txt").read_text(encoding="utf-8") == name
    assert (folder / "secondary-backup-target.json").is_file()
    assert (root / "unrelated.db").is_file()
    record = await catalogue.require(adopted)
    assert record.origin is UniverseOrigin.ADOPTED
    assert record.media_prefix == ""
    assert record.schema_revision
    assert json.loads((folder / "universe.json").read_text(encoding="utf-8"))["id"] == adopted
    assert await adopt_old_layout(catalogue) is None
    assert [item.id for item in await catalogue.every()] == [adopted]
    events, total = await catalogue.events()
    assert total == 1
    assert events[0].kind is LibraryEventKind.ADOPTED
    await catalogue.close()


async def test_an_interrupted_adoption_resumes_where_it_stopped(tmp_path: Path, schema_template: Path) -> None:
    root = tmp_path / "data"
    old_layout(root, schema_template)
    process = ProcessPaths(root)
    mark_adoption(process, "resumedabc12")
    halfway = process.universe("resumedabc12").root
    halfway.mkdir(parents=True)
    (root / "media").rename(halfway / "media")
    catalogue = Catalogue(process)
    assert await adopt_old_layout(catalogue) == "resumedabc12"
    assert (halfway / "media" / "kept.txt").is_file()
    assert (halfway / "backups" / "kept.txt").is_file()
    assert (halfway / "aerona.db").is_file()
    assert not process.adoption_marker.exists()
    assert (await catalogue.require("resumedabc12")).origin is UniverseOrigin.ADOPTED
    mark_adoption(process, "resumedabc12")
    assert await adopt_old_layout(catalogue) == "resumedabc12"
    assert len(await catalogue.every()) == 1
    await catalogue.close()


async def test_a_fresh_library_starts_empty(tmp_path: Path) -> None:
    catalogue = Catalogue(ProcessPaths(tmp_path / "data"))
    assert await prepare_library(catalogue) is None
    assert await catalogue.every() == []
    assert (tmp_path / "data" / "library.db").is_file()
    await catalogue.close()


async def test_a_universe_folder_without_its_catalogue_row_is_shelved_again(tmp_path: Path, schema_template: Path) -> None:
    root = tmp_path / "data"
    old_layout(root, schema_template)
    first = Catalogue(ProcessPaths(root))
    adopted = await prepare_library(first)
    assert adopted is not None
    await first.close()
    (root / "library.db").unlink()
    again = Catalogue(ProcessPaths(root))
    assert await prepare_library(again) is None
    records = await again.every()
    assert [record.id for record in records] == [adopted]
    assert records[0].origin is UniverseOrigin.ADOPTED
    await again.close()
