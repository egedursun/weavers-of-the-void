import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
NODE_CLASSES = frozenset({"StarRow", "WorldRow", "DimensionRow", "ClusterRow", "GalaxyRow", "CreatorRow", "EntityRow", "ForeignGodRow", "SonRow"})


@dataclass(frozen=True)
class Join:
    path: Path
    line: int
    classes: tuple[str, ...]


def named(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name) and node.id in NODE_CLASSES:
        return node.id
    if isinstance(node, ast.Attribute):
        return named(node.value)
    return None


def chain_calls(node: ast.AST) -> list[ast.Call]:
    found: list[ast.Call] = []
    while isinstance(node, ast.Call):
        found.append(node)
        func = node.func
        node = func.value if isinstance(func, ast.Attribute) else func
    return found


def joins(files: dict[Path, str]) -> list[Join]:
    found: list[Join] = []
    for path, text in files.items():
        seen: set[int] = set()
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call) or id(node) in seen:
                continue
            calls = chain_calls(node)
            seen.update(id(call) for call in calls)
            names = [call.func.attr if isinstance(call.func, ast.Attribute) else call.func.id if isinstance(call.func, ast.Name) else "" for call in calls]
            if "select" not in names:
                continue
            classes = {name for call in calls for arg in call.args for name in [named(arg)] if name is not None}
            joined = any(
                isinstance(call.func, ast.Attribute)
                and call.func.attr in {"join", "outerjoin"}
                and call.args
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id in NODE_CLASSES
                for call in calls
            )
            if joined and len(classes) >= 2:
                found.append(Join(path, node.lineno, tuple(sorted(classes))))
    return found


def main() -> int:
    found = joins({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: joins {', '.join(item.classes)}, which share the nodes table; alias one with aliased(..., flat=True) or read them apart"
        )
    print(f"node joins: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
