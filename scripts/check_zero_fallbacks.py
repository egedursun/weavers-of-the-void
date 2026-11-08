import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
COUNTS = frozenset({"stat"})
DISTANCES = frozenset({"region_hops", "hops", "distance"})


@dataclass(frozen=True)
class Fallback:
    path: Path
    line: int
    text: str


def called(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None


def zero(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value == 0


def fallbacks(files: dict[Path, str]) -> list[Fallback]:
    found: list[Fallback] = []
    for path, text in files.items():
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.BoolOp) or not isinstance(node.op, ast.Or):
                continue
            name = called(node.values[0])
            if name in COUNTS | DISTANCES and not (len(node.values) == 2 and zero(node.values[1])):
                found.append(Fallback(path, node.lineno, ast.unparse(node)))
    return found


def main() -> int:
    found = fallbacks({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} treats a true zero as missing; use stat_or or an explicit None check")
    print(f"zero fallbacks: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
