import ast
import importlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from aerona.catalog.season_positions import (
    RATE_WORD,
    SEASON_NAME,
    SEASON_POSITIONS,
    SEASON_STEPS,
)
from aerona.db.base import Base

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
REMAPPERS = (
    "engine/environment/season_remap.py",
    "services/integrity/season_positions.py",
)
SKIPPED = ("db/alembic/", "db/tables/")
MODELS = "aerona.db.tables"


@dataclass(frozen=True)
class Finding:
    where: str
    text: str


def season_columns() -> list[tuple[str, str]]:
    importlib.import_module(MODELS)
    found = []
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            if (
                re.fullmatch(SEASON_NAME, column.name)
                and RATE_WORD not in column.name
                and column.type.python_type is int
            ):
                found.append((table.name, column.name))
    return sorted(found)


def unclassified(columns: list[tuple[str, str]]) -> list[Finding]:
    known = {(entry.table, entry.column) for entry in SEASON_POSITIONS} | {
        (entry.table, entry.column) for entry in SEASON_STEPS
    }
    missing = [
        Finding(
            f"{table}.{column}",
            "holds a season but is in neither SEASON_POSITIONS nor SEASON_STEPS",
        )
        for table, column in columns
        if (table, column) not in known
    ]
    gone = [
        Finding(f"{table}.{column}", "is registered but no such season column exists")
        for table, column in sorted(known - set(columns))
    ]
    return missing + gone


def class_names() -> dict[str, str]:
    importlib.import_module(MODELS)
    return {
        mapper.local_table.name: mapper.class_.__name__
        for mapper in Base.registry.mappers
    }


def writes_in(relative: str, text: str, watched: dict[str, set[str]]) -> list[Finding]:
    tree = ast.parse(text)
    imported = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    columns = {
        column for name, cols in watched.items() if name in imported for column in cols
    }
    found: list[Finding] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in watched
            and node.func.id in imported
        ):
            found.extend(
                Finding(
                    f"backend/src/aerona/{relative}:{node.lineno}",
                    f"{node.func.id}({word.arg}=…)",
                )
                for word in node.keywords
                if word.arg in watched[node.func.id]
            )
        if isinstance(node, ast.Assign | ast.AugAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            found.extend(
                Finding(
                    f"backend/src/aerona/{relative}:{node.lineno}", ast.unparse(target)
                )
                for target in targets
                if isinstance(target, ast.Attribute) and target.attr in columns
            )
    return found


def stray_writes() -> list[Finding]:
    names = class_names()
    found: list[Finding] = []
    for path in sorted(SOURCE.rglob("*.py")):
        relative = str(path.relative_to(SOURCE))
        if relative.startswith(SKIPPED) or "alembic" in relative.split("/") or relative in REMAPPERS:
            continue
        watched: dict[str, set[str]] = {}
        for entry in SEASON_POSITIONS:
            if relative not in entry.writers:
                watched.setdefault(names[entry.table], set()).add(entry.column)
        found.extend(writes_in(relative, path.read_text(encoding="utf-8"), watched))
    return found


def main() -> int:
    found = unclassified(season_columns()) + stray_writes()
    for item in found:
        print(
            f"{item.where}: {item.text}; register the column in catalog/season_positions.py, or write it only from its own writers"
        )
    print(f"season position problems: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
