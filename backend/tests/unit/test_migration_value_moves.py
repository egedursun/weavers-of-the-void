import ast
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

VERSIONS = Path(__file__).resolve().parents[2] / "src" / "aerona" / "db" / "alembic" / "versions"
MOVING_CONSTANTS = ("RENAMED", "MOVED_AREAS")
UPDATE_TARGET = re.compile(r"UPDATE (\w+) SET (\w+) =")


def loaded(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def new_values(module: ModuleType, constant: str, helper_source: str) -> list[tuple[str, str, str]]:
    rows: tuple[Any, ...] = getattr(module, constant, ())
    if constant == "RENAMED":
        return [(row[0], row[1], row[3]) for row in rows]
    target = UPDATE_TARGET.search(helper_source)
    if target is None:
        return []
    return [(target.group(1), target.group(2), row[2]) for row in rows]


def unsafe_moves(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    if "RETYPED" not in source or not any(constant in source for constant in MOVING_CONSTANTS):
        return []
    module = loaded(path)
    allowed = {(row[0], row[1]): set(row[3]) for row in getattr(module, "RETYPED", ())}
    tree = ast.parse(source)
    helpers = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    upgrade = helpers.get("upgrade")
    if upgrade is None:
        return []
    found: list[str] = []
    widened = False
    for statement in upgrade.body:
        if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and isinstance(statement.value.func, ast.Name)):
            continue
        name = statement.value.func.id
        if name == "widen":
            widened = True
        helper = helpers.get(name)
        if helper is None or widened:
            continue
        helper_source = ast.get_source_segment(source, helper) or ""
        for constant in MOVING_CONSTANTS:
            if f"in {constant}" not in helper_source:
                continue
            for table, column, value in new_values(module, constant, helper_source):
                if (table, column) in allowed and value not in allowed[(table, column)]:
                    found.append(f"{path.name}: {name}() writes {table}.{column} = {value!r} before the column allows it; call widen() first")
    return found


def test_no_migration_writes_a_value_its_enum_column_does_not_allow_yet() -> None:
    assert [problem for path in sorted(VERSIONS.glob("*.py")) for problem in unsafe_moves(path)] == []


def test_the_guard_finds_a_move_ahead_of_the_widening(tmp_path: Path) -> None:
    bad = tmp_path / "bad_migration.py"
    bad.write_text(
        'RETYPED = (("law_profiles", "area", "area", ("fiscal",), ("fiscal", "faith"), False),)\n'
        'MOVED_AREAS = (("tithe", "fiscal", "faith"),)\n'
        "def move_areas(forward):\n"
        "    for kind, old, new in MOVED_AREAS:\n"
        "        print(f\"UPDATE law_profiles SET area = '{new}' WHERE kind = '{kind}'\")\n"
        "def retype(forward):\n    pass\n"
        "def widen(forward):\n    pass\n"
        "def upgrade():\n    move_areas(True)\n    retype(True)\n",
        encoding="utf-8",
    )
    good = tmp_path / "good_migration.py"
    good.write_text(
        bad.read_text(encoding="utf-8").replace("    move_areas(True)\n    retype(True)", "    widen(True)\n    move_areas(True)\n    retype(True)"),
        encoding="utf-8",
    )
    assert len(unsafe_moves(bad)) == 1
    assert unsafe_moves(good) == []
