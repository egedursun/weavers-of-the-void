import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
SCANNED = (SOURCE / "engine", SOURCE / "services", SOURCE / "agents", SOURCE / "api")
AWARE = frozenset({"parent_world_id", "root_of", "host_of", "root_world"})
ROOTS = frozenset({"root", "host", "moon", "planet"})


@dataclass(frozen=True)
class Read:
    path: Path
    line: int
    function: str


def aware(function: ast.AST) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Attribute) and node.attr in AWARE:
            return True
        if isinstance(node, ast.Name) and node.id in AWARE:
            return True
    return False


def orbit_reads(function: ast.AST) -> list[ast.Attribute]:
    return [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Attribute)
        and node.attr == "orbit"
        and isinstance(node.ctx, ast.Load)
        and not (isinstance(node.value, ast.Name) and node.value.id in ROOTS)
    ]


def reads(files: dict[Path, str]) -> list[Read]:
    found: list[Read] = []
    for path, text in files.items():
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or aware(node):
                continue
            found.extend(Read(path, item.lineno, node.name) for item in orbit_reads(node))
    return found


def sources() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for folder in SCANNED for path in sorted(folder.rglob("*.py"))}


def main() -> int:
    found = reads(sources())
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.function} reads a world's orbit without telling a moon from a planet; "
            "a moon's orbit is around its planet, so read the planet's through root_of or check parent_world_id"
        )
    print(f"moon orbits: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
