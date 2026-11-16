import argparse
import ast
import re
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "backend" / "src" / "aerona"
TESTS = ROOT / "backend" / "tests"
FRONTEND = ROOT / "frontend" / "src"
FRONT_SCRIPTS = ROOT / "frontend" / "scripts"
INVENTORY = ROOT / "docs" / "spec" / "inventory.md"
COLUMNS = ("Axis", "Item", "Proven by", "Open layers and the rows that close them")
SKIPPED = frozenset({"__pycache__", "alembic", ".mypy_cache"})
ENUM_BASES = frozenset({"StrEnum", "IntEnum", "Enum"})
TABLE = re.compile(r'__tablename__ = "([a-z0-9_]+)"')
PHASE = re.compile(r'\bPhase\("([a-z0-9_]+)"')
INCIDENT = re.compile(r'\b(?:template_key|key)="([a-z][a-z0-9_]*\.[a-z0-9_.]+)"')
LEVER = re.compile(r'@player_action\(\s*"([a-z0-9_:]+)"')
TOOL = re.compile(r'^\s+([A-Z][A-Z0-9_]+) = "([a-z0-9_]+)"', re.MULTILINE)
SCREEN = re.compile(r"^export function ([A-Z]\w+)", re.MULTILINE)
PROMPT_SUFFIXES = frozenset({".j2", ".md", ".json", ".txt", ".yaml", ".yml"})


@dataclass(frozen=True)
class Axis:
    name: str
    proven: tuple[str, ...]
    open_layers: tuple[str, ...]
    found: Callable[[], Iterable[str]]


def sources(root: Path, suffix: str = ".py") -> list[Path]:
    return [path for path in sorted(root.rglob(f"*{suffix}")) if not SKIPPED & set(path.parts)]


def matches(pattern: re.Pattern[str], root: Path, suffix: str = ".py") -> set[str]:
    return {match for path in sources(root, suffix) for match in pattern.findall(path.read_text(encoding="utf-8"))}


def tables() -> set[str]:
    return matches(TABLE, PACKAGE / "db" / "tables")


def enum_types() -> set[str]:
    found: set[str] = set()
    for path in sources(PACKAGE):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef) and any(isinstance(base, ast.Name) and base.id in ENUM_BASES for base in node.bases):
                found.add(f"{path.relative_to(PACKAGE).with_suffix('')}.{node.name}".replace("/", "."))
    return found


def steps() -> set[str]:
    return matches(PHASE, PACKAGE / "engine")


def incident_kinds() -> set[str]:
    return matches(INCIDENT, PACKAGE / "engine") | matches(INCIDENT, PACKAGE / "services")


def tools() -> set[str]:
    text = (PACKAGE / "prompts" / "tools" / "ids.py").read_text(encoding="utf-8")
    son, mortal = text.split("class MortalToolId", 1)
    return {f"son:{value}" for _member, value in TOOL.findall(son)} | {f"mortal:{value}" for _member, value in TOOL.findall(mortal)}


def levers() -> set[str]:
    return matches(LEVER, PACKAGE / "services")


def screens() -> set[str]:
    return {f"{path.relative_to(FRONTEND).parent}/{name}" for path in sources(FRONTEND, ".tsx") if ".test." not in path.name for name in SCREEN.findall(path.read_text(encoding="utf-8"))}


def model_texts() -> set[str]:
    return {str(path.relative_to(PACKAGE)) for path in sorted((PACKAGE / "prompts").rglob("*")) if path.is_file() and path.suffix in PROMPT_SUFFIXES and not SKIPPED & set(path.parts)}


AXES = (
    Axis(
        "table",
        ("check_wiring.py", "check_control.py", "test_frontend_reads_every_field.py", "test_god_control.py"),
        ("integrity of every value: 47.13", "history, changes, moments and terms: F58.5", "F58.6", "F58.7"),
        tables,
    ),
    Axis("enum", ("check_wiring.py", "check_label_maps.py", "check_raw_enums.mjs"), ("every value read: 47.7", "two layers for content concepts: W48"), enum_types),
    Axis("step", ("test_god_control.py", "test_eager_epochs.py"), ("each write recorded with its happening: F58.5",), steps),
    Axis("incident", ("check_canned_lines.py",), ("roles, facts, steps, template, place and clock: F58.1",), incident_kinds),
    Axis("tool", ("test_every_tool.py", "test_catalogue.py", "test_tool_enum_lists.py"), (), tools),
    Axis("lever", ("test_every_lever.py", "test_unique_levers.py", "check_wiring.py"), ("revert of any change: 49.5",), levers),
    Axis("screen", ("check_hidden_controls.py", "check_raw_ids.py", "check_frontend_orphans.py", "test_frontend_reads_every_field.py"), (), screens),
    Axis("text", ("check_prompt_bias.py", "check_canned_lines.py"), ("a full read against rule 2: 47.14",), model_texts),
)


def guard_exists(name: str) -> bool:
    if (ROOT / "scripts" / name).exists() or (FRONT_SCRIPTS / name).exists():
        return True
    return any(TESTS.rglob(name))


def rows() -> list[tuple[str, str, str, str]]:
    found: list[tuple[str, str, str, str]] = []
    for axis in AXES:
        proven = "; ".join(axis.proven) or "—"
        open_layers = "; ".join(axis.open_layers) or "none"
        found += [(axis.name, item, proven, open_layers) for item in sorted(axis.found())]
    return found


def render(found: list[tuple[str, str, str, str]]) -> str:
    counts = {axis.name: sum(1 for row in found if row[0] == axis.name) for axis in AXES}
    lines = [
        "# Inventory of countable things",
        "",
        "One row for every table, enum type, engine step, incident kind, agent tool, god lever, screen and model-facing text file (spec 16, 5.10 and 6.7).",
        "Each row names the guards that prove it against rules 1–8 and the layers of 6.6, and the spec rows that close what no guard proves yet.",
        "Generated and checked by `scripts/check_inventory.py`; the commit gate fails when the code holds a thing without a row or a row names a guard that does not exist.",
        "",
        "| Axis | Count |",
        "|---|---|",
        *[f"| {name} | {count} |" for name, count in counts.items()],
        "",
        "| " + " | ".join(COLUMNS) + " |",
        "|" + "|".join("---" for _ in COLUMNS) + "|",
        *["| " + " | ".join(row) + " |" for row in found],
        "",
    ]
    return "\n".join(lines)


def problems(found: list[tuple[str, str, str, str]]) -> list[str]:
    issues: list[str] = []
    written = INVENTORY.read_text(encoding="utf-8") if INVENTORY.exists() else ""
    kept = {tuple(cell.strip() for cell in line.strip().strip("|").split("|")) for line in written.splitlines() if line.startswith("| ") and line.count("|") == len(COLUMNS) + 1}
    issues += [f"{axis} {item} has no row in {INVENTORY.relative_to(ROOT)}" for axis, item, *_ in found if not any(row[:2] == (axis, item) for row in kept)]
    present = {(axis, item) for axis, item, *_ in found}
    issues += [f"row {row[0]} {row[1]} names nothing the code holds" for row in kept if row[0] in {axis.name for axis in AXES} and row[:2] not in present]
    guards = {guard for axis in AXES for guard in axis.proven}
    issues += [f"guard {guard} does not exist" for guard in sorted(guards) if not guard_exists(guard)]
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("write", "check"))
    mode = parser.parse_args().mode
    found = rows()
    if mode == "write":
        INVENTORY.write_text(render(found), encoding="utf-8")
        print(f"inventory: {len(found)} rows written")
        return 0
    issues = problems(found)
    for issue in issues:
        print(issue)
    print(f"inventory: {len(found)} things, {len(issues)} problem(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
