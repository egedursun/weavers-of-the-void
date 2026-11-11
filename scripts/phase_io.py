import argparse
import asyncio
import inspect
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from alembic import command

from aerona.db import tables
from aerona.db.base import Base
from aerona.db.migrations import build_config, upgrade_to_head
from aerona.db.session import Database
from aerona.engine.interconnect.annotations import declared_reads, declared_writes
from aerona.engine.interconnect.guards import READ_MODE, recording
from aerona.engine.interconnect.table_io import install_table_recorder
from aerona.engine.pipeline import all_phases, simulate
from tests.engine.integration.factories import seed_rich_cosmos

assert tables

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DECORATOR = re.compile(r"^@(reads|writes)\(")
IMPORT_LINE = "from aerona.engine.interconnect.annotations import reads, writes"


async def record_seeded(epochs: int) -> dict[str, set[tuple[str, str]]]:
    recorder: dict[str, set[tuple[str, str]]] = {}
    with tempfile.TemporaryDirectory() as folder:
        url = f"sqlite+aiosqlite:///{folder}/io.db"
        database = Database(url)
        try:
            async with database.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            await asyncio.to_thread(command.stamp, build_config(url), "head")
            async with database.write() as session:
                await seed_rich_cosmos(session)
            with recording(recorder):
                await simulate(database, epochs)
        finally:
            await database.dispose()
    return recorder


async def record_copy(path: Path, epochs: int) -> dict[str, set[tuple[str, str]]]:
    recorder: dict[str, set[tuple[str, str]]] = {}
    url = f"sqlite+aiosqlite:///{path}"
    await upgrade_to_head(url)
    database = Database(url)
    try:
        with recording(recorder):
            await simulate(database, epochs)
    finally:
        await database.dispose()
    return recorder


def merge(target: dict[str, set[tuple[str, str]]], source: dict[str, set[tuple[str, str]]]) -> None:
    for phase, items in source.items():
        target.setdefault(phase, set()).update(items)


def without_annotations(lines: list[str], first: int) -> tuple[list[str], int]:
    end = first
    while not lines[end].lstrip().startswith(("def ", "async def ")):
        end += 1
    kept: list[str] = []
    dropping = False
    for item in lines[first:end]:
        if item.startswith("@"):
            dropping = bool(DECORATOR.match(item))
        if not dropping:
            kept.append(item)
    return kept, end


def annotate(recorded: dict[str, set[tuple[str, str]]], *, rebuild: bool) -> list[Path]:
    wanted: dict[object, tuple[set[str], set[str]]] = {}
    for phase in all_phases():
        reads_now, writes_now = wanted.setdefault(phase.run, (set(), set()))
        if not rebuild:
            reads_now.update(declared_reads(phase.run))
            writes_now.update(declared_writes(phase.run))
        for mode, key in recorded.get(phase.name, set()):
            (reads_now if mode == READ_MODE else writes_now).add(key)
    by_file: dict[Path, list[tuple[int, set[str], set[str]]]] = defaultdict(list)
    for function, (reads_now, writes_now) in wanted.items():
        target = inspect.unwrap(function)
        if not inspect.isfunction(target) or not (reads_now or writes_now):
            continue
        source = Path(inspect.getsourcefile(target) or "")
        line = inspect.getsourcelines(target)[1]
        by_file[source].append((line, reads_now, writes_now))
    for source, entries in by_file.items():
        lines = source.read_text(encoding="utf-8").splitlines()
        for line, reads_now, writes_now in sorted(entries, reverse=True):
            first = line - 1
            kept, end = without_annotations(lines, first)
            insert = []
            if reads_now:
                insert.append("@reads(" + ", ".join(f'"{key}"' for key in sorted(reads_now)) + ")")
            if writes_now:
                insert.append("@writes(" + ", ".join(f'"{key}"' for key in sorted(writes_now)) + ")")
            lines[first:end] = kept + insert
        text = "\n".join(lines) + "\n"
        if IMPORT_LINE not in text:
            first = next(number for number, item in enumerate(lines) if item.startswith("from aerona."))
            lines.insert(first, IMPORT_LINE)
            text = "\n".join(lines) + "\n"
        source.write_text(text, encoding="utf-8")
    return sorted(by_file)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--copy", type=Path, help="a copy of a real world database to run as well")
    parser.add_argument("--rebuild", action="store_true", help="drop declared keys that no run observed")
    arguments = parser.parse_args()
    install_table_recorder()
    recorded = asyncio.run(record_seeded(arguments.epochs))
    if arguments.copy is not None:
        merge(recorded, asyncio.run(record_copy(arguments.copy, arguments.epochs)))
    changed = annotate(recorded, rebuild=arguments.rebuild)
    if changed:
        subprocess.run(["uv", "run", "ruff", "check", "--fix", "-q", *map(str, changed)], cwd=BACKEND, check=False)
        subprocess.run(["uv", "run", "ruff", "format", "-q", *map(str, changed)], cwd=BACKEND, check=False)
        subprocess.run(["uv", "run", "python", str(ROOT / "scripts" / "interconnection_docs.py"), "write"], cwd=BACKEND, check=True)
    print(f"annotated {sum(len(items) for items in recorded.values())} reads and writes across {len(recorded)} phases in {len(changed)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
