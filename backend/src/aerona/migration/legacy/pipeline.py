import sqlite3
import tempfile
from collections.abc import Awaitable, Callable
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import text

from aerona.constants.media import MediaBackend
from aerona.constants.migration import LEDGER_HISTORY_NAME, PARTIAL_SUFFIX, SNAPSHOT_NAME
from aerona.core.grammar import spoken
from aerona.db.migrations import upgrade_to_head
from aerona.db.session import Database
from aerona.media.store import MediaStore
from aerona.migration.legacy import finalize
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.errors import MigrationError, TargetExistsError
from aerona.migration.legacy.importers import chronicle, community, cosmos, entities, language, lore, meta, pantheon, rewards, state, travel
from aerona.migration.legacy.importers.bonds import import_bonds
from aerona.migration.legacy.importers.images import UploadLog, import_images, remove_uploads
from aerona.migration.legacy.ledger_history import import_ledger_history, ledger_history, write_ledger_history
from aerona.migration.legacy.markdown import render_markdown
from aerona.migration.legacy.media import open_media_store
from aerona.migration.legacy.report import MigrationReport, write_report
from aerona.migration.legacy.rules_map import map_overrides, override_rows
from aerona.migration.legacy.snapshot import take_snapshot
from aerona.migration.legacy.source import LegacySource
from aerona.migration.legacy.validation import validate
from aerona.migration.legacy.vocabulary import Vocabulary, load_vocabulary
from aerona.rules.registry import Rules
from aerona.rules.snapshot import apply_overrides
from aerona.settings import Settings

SQLITE_URL = "sqlite+aiosqlite:///{path}"
DRY_TARGET = "dry-run.db"
SIDE_FILES = ("-wal", "-shm", "-journal")
NOT_MIGRATED_TABLES = ("ledger", "ledger_rows", "llm_metrics", "live_feed")

Step = Callable[[MigrationContext], Awaitable[None]]


@dataclass(frozen=True)
class MigrationOptions:
    legacy_dir: Path
    target: Path
    dry_run: bool = False
    replace: bool = False
    media_backend: MediaBackend = MediaBackend.FILE
    media_dir: Path | None = None
    report_dir: Path | None = None
    settings: Settings = field(default_factory=Settings)
    store: MediaStore | None = None


def remove_database(path: Path) -> None:
    for candidate in (path, *(path.with_name(path.name + suffix) for suffix in SIDE_FILES)):
        candidate.unlink(missing_ok=True)


def fold_wal(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")


def work_path(options: MigrationOptions, workspace: Path) -> Path:
    if options.dry_run:
        return workspace / DRY_TARGET
    return options.target.with_name(options.target.name + PARTIAL_SUFFIX)


def steps() -> list[tuple[str, Step]]:
    return [
        ("sons", pantheon.import_sons),
        ("world_gods", cosmos.link_world_gods),
        ("foreign_gods", pantheon.import_foreign_gods),
        ("entities", _entities),
        ("son_links", pantheon.link_son_entities),
        ("epoch_stars", cosmos.link_world_stars),
        ("bonds", import_bonds),
        ("routes", travel.import_routes),
        ("chronicle", chronicle.import_chronicle),
        ("epochs", chronicle.import_epochs),
        ("facts", lore.import_facts),
        ("lexicon", lore.import_lexicon),
        ("world_phonology", language.derive_world_phonology),
        ("languages", language.import_language_profiles),
        ("threads", lore.import_threads),
        ("rewards", rewards.import_rewards),
        ("messages", lore.import_messages),
        ("councils", lore.import_councils),
        ("folk_beliefs", lore.import_folk_beliefs),
        ("network_reviews", lore.import_network_reviews),
        ("community_relations", community.import_community_relations),
        ("societies", community.import_societies),
        ("journeys", travel.import_journeys),
        ("state", state.convert_state),
        ("scores", meta.import_scores),
        ("notifications", meta.import_notifications),
        ("map_notes", meta.import_map_notes),
        ("map_snapshots", meta.import_map_snapshots),
        ("epoch_stats", meta.import_epoch_stats),
    ]


async def _entities(context: MigrationContext) -> None:
    await entities.import_entities(context)


def source_counts(source: LegacySource, vocabulary: Vocabulary, report: MigrationReport) -> None:
    for name, table in vocabulary.tables.items():
        if source.has(name):
            report.source_counts[table.name] = source.count(name)
    for name in NOT_MIGRATED_TABLES:
        report.not_migrated[vocabulary.table(name).name] = source.count(name)


async def migrate_into(
    options: MigrationOptions, source: LegacySource, report: MigrationReport, database: Database, *, store: MediaStore, log: UploadLog
) -> None:
    vocabulary = source.vocabulary
    state_row = source.single("world_state")
    if state_row is None:
        raise MigrationError("The legacy world state is missing.")
    overrides = map_overrides(vocabulary, state_row, report)
    rules = apply_overrides(Rules(), overrides)
    async with database.write() as session:
        await session.execute(text("PRAGMA defer_foreign_keys = ON"))
        context = MigrationContext(session=session, source=source, vocabulary=vocabulary, report=report, rules=rules, epoch=report.legacy_epoch or 1)
        await cosmos.import_stars(context)
        await cosmos.import_worlds(context)
        await cosmos.import_cosmos(context, state_row)
        await cosmos.import_creator(context, state_row)
        for _, step in steps():
            await step(context)
        await import_images(context, store, options.legacy_dir, log)
        report.not_migrated["ledger_pages_as_history"] = await import_ledger_history(session, ledger_history(source))
        session.add_all(override_rows(overrides))
        await session.flush()
        await finalize.run_repairs(context)
        await finalize.type_species(context)
        await finalize.regenerate_maps(context)
        await finalize.check_constraints(context)
        await finalize.count_tables(context)


async def run_migration(options: MigrationOptions) -> MigrationReport:
    vocabulary = load_vocabulary()
    backend = options.media_backend.value if not options.dry_run else f"{spoken(options.media_backend)} (dry run)"
    report = MigrationReport(legacy_path=str(options.legacy_dir), target_path=str(options.target), dry_run=options.dry_run, media_backend=backend)
    if not options.dry_run and options.target.exists() and not options.replace:
        raise TargetExistsError(f"{options.target} already exists; pass --replace to overwrite it.")
    log = UploadLog()
    store = options.store or open_media_store(options.media_backend, options.media_dir, options.settings, options.dry_run)
    with tempfile.TemporaryDirectory() as workspace_name:
        workspace = Path(workspace_name)
        snapshot = take_snapshot(options.legacy_dir / vocabulary.database_file, workspace / SNAPSHOT_NAME)
        source = LegacySource(snapshot, vocabulary)
        work = work_path(options, workspace)
        try:
            validate(source, report)
            source_counts(source, vocabulary, report)
            remove_database(work)
            work.parent.mkdir(parents=True, exist_ok=True)
            await upgrade_to_head(SQLITE_URL.format(path=work))
            await store.ensure_ready()
            database = Database(SQLITE_URL.format(path=work))
            try:
                await migrate_into(options, source, report, database, store=store, log=log)
            finally:
                await database.dispose()
            if not options.dry_run:
                fold_wal(work)
                if options.target.exists():
                    remove_database(options.target)
                work.replace(options.target)
                report.not_migrated["ledger_kept_as_history"] = write_ledger_history(source, options.target.with_name(LEDGER_HISTORY_NAME))
            report.finish()
        except Exception as error:
            await remove_uploads(store, log)
            remove_database(work)
            report.finish(f"{type(error).__name__}: {error}")
            raise
        finally:
            source.close()
            if options.store is None:
                await store.close()
            directory = options.report_dir or (None if options.dry_run else options.target.parent)
            if directory is not None:
                write_report(report, directory, render_markdown(report))
    return report
