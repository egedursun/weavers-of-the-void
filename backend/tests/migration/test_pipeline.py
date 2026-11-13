import hashlib
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

import pytest

from aerona.constants.migration import LEDGER_HISTORY_NAME, PARTIAL_SUFFIX, REPORT_JSON_NAME, REPORT_MARKDOWN_NAME
from aerona.media.file_store import FileMediaStore
from aerona.media.store import MediaStore
from aerona.migration.legacy import finalize
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.errors import LegacyValidationError, MigrationError, TargetExistsError
from aerona.migration.legacy.pipeline import MigrationOptions, run_migration
from aerona.migration.legacy.report import MigrationReport
from tests.migration.legacy_fixture import LegacyFixture

Query = Callable[[str], list[tuple[object, ...]]]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def query(path: Path) -> Query:
    def run(statement: str) -> list[tuple[object, ...]]:
        with closing(sqlite3.connect(path)) as connection:
            return list(connection.execute(statement))

    return run


def options(legacy: LegacyFixture, tmp_path: Path, *, dry_run: bool = False, store: MediaStore | None = None) -> MigrationOptions:
    return MigrationOptions(
        legacy_dir=legacy.directory,
        target=tmp_path / "out" / "aerona.db",
        media_dir=tmp_path / "out" / "media",
        report_dir=tmp_path / "reports",
        dry_run=dry_run,
        store=store,
    )


@pytest.fixture
async def migrated(legacy: LegacyFixture, tmp_path: Path) -> tuple[MigrationReport, Query, Path]:
    before = digest(legacy.path)
    report = await run_migration(options(legacy, tmp_path))
    assert digest(legacy.path) == before
    return report, query(tmp_path / "out" / "aerona.db"), tmp_path


async def test_round_trip_counts(migrated: tuple[MigrationReport, Query, Path]) -> None:
    report, run, _ = migrated
    assert report.succeeded
    assert run("SELECT lore_language, epoch, epoch_start_year FROM cosmos") == [("turkish", 5, 200)]
    assert run("SELECT COUNT(*) FROM entities") == [(14,)]
    assert run("SELECT COUNT(*) FROM sons") == [(2,)]
    assert run("SELECT COUNT(*) FROM chronicle") == [(4,)]
    assert run("SELECT COUNT(*) FROM chronicle WHERE visible = 0") == [(1,)]
    assert run("SELECT COUNT(*) FROM chronicle_entities") == [(7,)]
    assert run("SELECT COUNT(*) FROM lexemes") == [(1,)]
    assert run("SELECT COUNT(*) FROM son_relations") == [(1,)]
    assert run("SELECT COUNT(*) FROM foreign_god_powers") == [(1,)]
    assert run("SELECT predicate, deterministic FROM canon_facts") == [("is located in", 1)]
    assert run("SELECT request, wish FROM messages") == [("wish", "a free wish")]
    assert report.checks == {"foreign_keys": "passed", "integrity": "passed", "name_registry": "passed"}
    assert any(item.category == "bond" for item in report.unplaced)
    assert report.conversions["duplicate_active_bonds_closed"] == 1


async def test_names_are_deduplicated_with_roman_numerals(migrated: tuple[MigrationReport, Query, Path]) -> None:
    report, run, _ = migrated
    names = sorted(str(row[0]) for row in run("SELECT n.name FROM entities e JOIN nodes n ON n.id = e.id WHERE e.entity_type IN ('settlement', 'place')"))
    assert names == ["Hamlet", "Hamlet II"]
    assert [(item.original, item.migrated) for item in report.renames] == [("Hamlet", "Hamlet II")]
    assert run("SELECT COUNT(*) FROM name_registry WHERE display = 'Gone'") == [(0,)]


async def test_typed_state_is_converted(migrated: tuple[MigrationReport, Query, Path]) -> None:
    report, run, _ = migrated
    assert run("SELECT status, score, battles, started_epoch FROM wars") == [("ongoing", 2, 3, 3)]
    assert run("SELECT side FROM war_sides ORDER BY side") == [("attacker",), ("defender",)]
    assert run("SELECT COUNT(*) FROM armies WHERE war_id IS NOT NULL") == [(1,)]
    assert run("SELECT status FROM tributes") == [("active",)]
    assert run("SELECT status, war_id IS NOT NULL FROM captives") == [("held", 1)]
    assert run("SELECT debt_amount, debt_what, debt_due_epoch, debt_status FROM bonds WHERE kind = 'owes'") == [(40, "grain", 7, "open")]
    assert run("SELECT truce_until_epoch FROM bonds WHERE kind = 'truce'") == [(8,)]
    assert run("SELECT civ_tier FROM entities WHERE civ_tier IS NOT NULL") == [(2,)]
    assert run("SELECT share_farmer, stock_food FROM community_societies") == [(50.0, 300)]
    assert run("SELECT COUNT(*) FROM reverences") == [(1,)]
    assert run("SELECT is_water FROM entities WHERE is_water = 1") == [(1,)]
    assert run("SELECT knowledge_branch FROM entities WHERE knowledge_branch IS NOT NULL") == [("writing",)]
    assert run("SELECT flag FROM entity_flags") == [("lost",)]
    assert run("SELECT trait FROM entity_traits") == [("flying",)]
    assert run("SELECT p.species_class FROM species_profiles p JOIN nodes n ON n.id = p.species_entity_id WHERE n.name = 'Sedge'") == [("plant",)]
    assert run("SELECT COUNT(*) FROM plant_profiles") == [(1,)]
    assert report.repairs["species_classes"] == 1
    assert run("SELECT writing_system, json_extract(signature, '$.consonants') FROM language_profiles") == [("alphabet", "lmn")]
    assert run("SELECT namespace, key, value FROM rule_overrides") == [("balance", "apocalypse_threshold", 500.0)]
    assert {rule.status for rule in report.rules} == {"applied", "unmapped"}
    assert "mystery:thing" in report.free_tags
    assert report.unknown_tags == {}
    assert run("SELECT COUNT(*) FROM world_maps") == [(2,)]
    assert run("SELECT origin FROM entities e JOIN nodes n ON n.id = e.id WHERE n.name = 'Ola'") == [("mortal",)]
    assert run(
        "SELECT json_extract(genesis_settings, '$.template'), json_extract(genesis_settings, '$.danger'), "
        "json_extract(genesis_settings, '$.technology'), json_extract(genesis_settings, '$.cosmos_size'), json_extract(genesis_settings, '$.tone') FROM cosmos"
    ) == [("mythic_age", 30, "bronze", "small", "solemn")]


async def test_images_are_deduplicated_and_linked(migrated: tuple[MigrationReport, Query, Path]) -> None:
    report, run, tmp_path = migrated
    images = report.images
    assert (images.rows, images.linked, images.uploaded, images.deduplicated, images.skipped_thumbnails) == (3, 3, 2, 1, 1)
    keys = run("SELECT object_key FROM images ORDER BY id")
    assert keys[0] == keys[1] and keys[0] != keys[2]
    assert run("SELECT caption, is_cover FROM images ORDER BY id LIMIT 1") == [("Northfolk at dawn", 1)]
    stored = sorted(path.name for path in (tmp_path / "out" / "media").rglob("*") if path.is_file())
    assert stored == ["a.png", "c.png"]


async def test_reports_and_history_are_written(migrated: tuple[MigrationReport, Query, Path]) -> None:
    _, _, tmp_path = migrated
    assert (tmp_path / "reports" / REPORT_JSON_NAME).is_file()
    assert "Legacy world migration" in (tmp_path / "reports" / REPORT_MARKDOWN_NAME).read_text(encoding="utf-8")
    assert (tmp_path / "out" / LEDGER_HISTORY_NAME).is_file()


async def test_dry_run_writes_nothing(legacy: LegacyFixture, tmp_path: Path) -> None:
    before = digest(legacy.path)
    report = await run_migration(options(legacy, tmp_path, dry_run=True))
    assert report.succeeded and report.dry_run
    assert not (tmp_path / "out").exists()
    assert (tmp_path / "reports" / REPORT_MARKDOWN_NAME).is_file()
    assert digest(legacy.path) == before


async def test_failure_rolls_everything_back(legacy: LegacyFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def explode(_context: MigrationContext) -> None:
        raise MigrationError("boom")

    monkeypatch.setattr(finalize, "check_constraints", explode)
    store_root = tmp_path / "out" / "media"
    with pytest.raises(MigrationError):
        await run_migration(options(legacy, tmp_path, store=FileMediaStore(store_root)))
    target = tmp_path / "out" / "aerona.db"
    assert not target.exists()
    assert not target.with_name(target.name + PARTIAL_SUFFIX).exists()
    assert store_root.exists()
    assert not any(path.is_file() for path in store_root.rglob("*"))
    assert "boom" in (tmp_path / "reports" / REPORT_MARKDOWN_NAME).read_text(encoding="utf-8")


async def test_existing_target_is_refused_without_replace(legacy: LegacyFixture, tmp_path: Path) -> None:
    target = tmp_path / "out" / "aerona.db"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"keep")
    with pytest.raises(TargetExistsError):
        await run_migration(options(legacy, tmp_path))
    assert target.read_bytes() == b"keep"


async def test_paused_epoch_is_rejected(legacy: LegacyFixture, tmp_path: Path) -> None:
    with closing(sqlite3.connect(legacy.path)) as connection:
        spec = legacy.vocabulary.table("world_state")
        connection.execute(f'UPDATE "{spec.name}" SET "{spec.physical("epoch_state")}" = ?', ('{"x": 1}',))
        connection.commit()
    with pytest.raises(LegacyValidationError):
        await run_migration(options(legacy, tmp_path, dry_run=True))
