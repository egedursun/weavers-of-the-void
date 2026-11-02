import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from aerona.constants.media import MediaBackend
from aerona.constants.paths import MEDIA_DIRNAME
from aerona.migration.legacy.errors import MigrationError
from aerona.migration.legacy.markdown import render_markdown
from aerona.migration.legacy.pipeline import MigrationOptions, run_migration

EXIT_FAILED = 1


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="aerona.migration.legacy", description="Migrate the legacy world into a fresh database.")
    command.add_argument("--legacy", type=Path, required=True, help="legacy data directory holding the database and the image folder")
    command.add_argument("--target", type=Path, required=True, help="path of the new database file")
    command.add_argument("--dry-run", action="store_true", help="convert into a throwaway database and only write the report")
    command.add_argument("--replace", action="store_true", help="overwrite an existing target database")
    command.add_argument("--media", choices=[backend.value for backend in MediaBackend], default=MediaBackend.FILE.value, help="media store")
    command.add_argument("--media-dir", type=Path, default=None, help="root of the file media store (default: next to the target)")
    command.add_argument("--report-dir", type=Path, default=None, help="where the migration reports are written")
    return command


def options_from(arguments: argparse.Namespace) -> MigrationOptions:
    target: Path = arguments.target.expanduser().resolve()
    backend = MediaBackend(arguments.media)
    media_dir = arguments.media_dir.expanduser().resolve() if arguments.media_dir is not None else None
    if backend is MediaBackend.FILE and media_dir is None:
        media_dir = target.parent / MEDIA_DIRNAME
    return MigrationOptions(
        legacy_dir=arguments.legacy.expanduser().resolve(),
        target=target,
        dry_run=arguments.dry_run,
        replace=arguments.replace,
        media_backend=backend,
        media_dir=media_dir,
        report_dir=arguments.report_dir.expanduser().resolve() if arguments.report_dir is not None else None,
    )


def main(argv: Sequence[str] | None = None) -> int:
    options = options_from(parser().parse_args(argv))
    try:
        report = asyncio.run(run_migration(options))
    except MigrationError as error:
        print(f"migration failed: {error}", file=sys.stderr)
        return EXIT_FAILED
    print(render_markdown(report))
    return 0
