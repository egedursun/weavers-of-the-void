import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
HOME = SOURCE / "engine" / "primitives" / "folk.py"
BLOCKS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)


@dataclass(frozen=True)
class Raw:
    path: Path
    line: int
    text: str


def located(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "location_id" and isinstance(node.value, ast.Name) and node.value.id == "EntityRow"


def raw_places(tree: ast.AST) -> Iterator[ast.AST]:
    for statement in ast.walk(tree):
        if not isinstance(statement, ast.stmt) or isinstance(statement, BLOCKS) or "EntityType.MORTAL" not in ast.unparse(statement):
            continue
        for node in ast.walk(statement):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq) and located(node.left):
                yield node
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "in_" and located(node.func.value):
                yield node


def raw_queries(files: dict[Path, str]) -> list[Raw]:
    return [Raw(path, node.lineno, ast.unparse(node)) for path, text in files.items() if path != HOME for node in raw_places(ast.parse(text))]


def main() -> int:
    found = raw_queries({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} finds mortals by a raw place; a people or polity holds none, use present_among or folk_among"
        )
    print(f"raw folk queries: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
