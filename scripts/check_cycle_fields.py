import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
HOME = "catalog/planetary_cycles.py"
SKIPPED = ("db/alembic/", "catalog/kinds/")
ENUM = "PlanetaryCycle"
NAMES = frozenset({"carbon", "water", "nutrients"})
FLOW_COLUMNS = frozenset(f"{name}_{side}" for name in NAMES for side in ("in", "out"))


@dataclass(frozen=True)
class Fixed:
    path: str
    line: int
    text: str


def aliases_of(tree: ast.Module) -> set[str]:
    names = {ENUM}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(
                alias.asname or alias.name for alias in node.names if alias.name == ENUM
            )
    return names


def is_member(node: ast.AST, names: set[str]) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in names
        and node.attr.isupper()
    )


def cycle_column(node: ast.AST) -> bool:
    if not isinstance(node, ast.Attribute):
        return False
    if node.attr in FLOW_COLUMNS:
        return True
    holder = (
        node.value.id
        if isinstance(node.value, ast.Name)
        else node.value.attr
        if isinstance(node.value, ast.Attribute)
        else ""
    )
    return node.attr in NAMES and "cycle" in holder.lower()


def named_list(node: ast.AST) -> bool:
    if not isinstance(node, ast.Set | ast.List | ast.Tuple):
        return False
    words = [
        item.value
        for item in node.elts
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    ]
    return sum(word in NAMES for word in words) >= 2 and len(words) == len(node.elts)


def fixed_in(relative: str, text: str) -> list[Fixed]:
    tree = ast.parse(text)
    names = aliases_of(tree)
    found: list[Fixed] = []
    for node in ast.walk(tree):
        listed = isinstance(node, ast.Set | ast.List | ast.Tuple | ast.Dict) and any(
            item is not None and is_member(item, names)
            for item in (node.keys if isinstance(node, ast.Dict) else node.elts)
        )
        compared = isinstance(node, ast.Compare) and any(
            is_member(side, names) for side in (node.left, *node.comparators)
        )
        if listed or compared or cycle_column(node) or named_list(node):
            found.append(
                Fixed(relative, getattr(node, "lineno", 0), ast.unparse(node)[:140])
            )
    return found


def fixed_cycles() -> list[Fixed]:
    found: list[Fixed] = []
    for path in sorted(SOURCE.rglob("*.py")):
        relative = str(path.relative_to(SOURCE))
        if relative == HOME or relative.startswith(SKIPPED):
            continue
        found.extend(fixed_in(relative, path.read_text(encoding="utf-8")))
    return sorted(set(found), key=lambda item: (item.path, item.line))


def main() -> int:
    found = fixed_cycles()
    for item in found:
        print(
            f"backend/src/aerona/{item.path}:{item.line}: {item.text} names a fixed planetary cycle; loop over CYCLES in catalog/planetary_cycles.py"
        )
    print(f"fixed cycle references: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
