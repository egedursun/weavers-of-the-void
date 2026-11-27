import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
HELPER = Path("db") / "fixups.py"
CREATION = Path("services") / "library" / "hub.py"
FIXUP_ROW = "AppliedFixupRow"
BORN_NAMES = {"BORN_CURRENT", "mark_born_current"}
BORN_TEXT = "universe.born_current"


def names_fixup_row(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == FIXUP_ROW
    if isinstance(node, ast.Attribute):
        return names_fixup_row(node.value)
    return False


def lookups(tree: ast.Module) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "get" and names_fixup_row(node.args[0]):
            found.append((node.lineno, "looks up a fixup key"))
        elif isinstance(func, ast.Name) and func.id == "select" and names_fixup_row(node.args[0]):
            found.append((node.lineno, "selects fixup keys"))
    return found


def born_marks(tree: ast.Module) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in BORN_NAMES:
            found.append((node.lineno, "names the born marker"))
        elif isinstance(node, ast.alias) and node.name in BORN_NAMES:
            found.append((getattr(node, "lineno", 0), "imports the born marker"))
        elif isinstance(node, ast.Constant) and node.value == BORN_TEXT:
            found.append((node.lineno, "writes the born marker"))
    return found


def problems_in(relative: Path, source: str) -> list[tuple[int, str]]:
    if relative == HELPER:
        return []
    tree = ast.parse(source)
    found = lookups(tree)
    if relative != CREATION:
        found += born_marks(tree)
    return found


def main() -> int:
    problems = [
        f"{path.relative_to(ROOT)}:{line} {what}"
        for path in sorted(SOURCE.rglob("*.py"))
        for line, what in problems_in(path.relative_to(SOURCE), path.read_text(encoding="utf-8"))
    ]
    for problem in problems:
        print(f"{problem}. Ask aerona.db.fixups: fixup_due for a one-time fixup, so a universe born current never rewrites what was authored in it, or marker and marked for a state marker it lists.")
    print(f"fixup keys: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
