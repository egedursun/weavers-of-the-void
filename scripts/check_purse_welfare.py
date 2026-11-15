import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
HOME = SOURCE / "engine" / "economy" / "purse.py"


@dataclass(frozen=True)
class Blend:
    path: Path
    line: int
    text: str


def blends(tree: ast.AST) -> list[ast.Call]:
    found: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "stat_or" or len(node.args) < 3:
            continue
        key, fallback = node.args[1], node.args[2]
        if isinstance(key, ast.Constant) and key.value == "wealth" and "prosperity" in ast.unparse(fallback):
            found.append(node)
    return found


def purse_blends(files: dict[Path, str]) -> list[Blend]:
    return [Blend(path, node.lineno, ast.unparse(node)) for path, text in files.items() if path != HOME for node in blends(ast.parse(text))]


def main() -> int:
    found = purse_blends({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        where = f"{item.path.relative_to(ROOT)}:{item.line}"
        print(f"{where}: {item.text} reads a purse as if it were how its people live; read prosperity for their lot, or riches_of for what can be taken")
    print(f"purses read as welfare: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
