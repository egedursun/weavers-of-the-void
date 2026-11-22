import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
HOME = SOURCE / "engine" / "primitives" / "levies.py"


@dataclass(frozen=True)
class Raw:
    path: Path
    line: int
    text: str


def headcount_put(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "put_stat"
        and len(node.args) >= 3
        and isinstance(node.args[2], ast.Call)
        and isinstance(node.args[2].func, ast.Name)
        and node.args[2].func.id == "headcount_key"
    )


def raw_returns(files: dict[Path, str]) -> list[Raw]:
    found: set[Raw] = set()
    for path, text in files.items():
        if path == HOME:
            continue
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and node.value is not None and headcount_put(node.value):
                found.add(Raw(path, node.lineno, ast.unparse(node)))
    return sorted(found, key=lambda item: (str(item.path), item.line))


def main() -> int:
    found = raw_returns({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} counts the heads it added by hand; a floor can raise a headcount past the heads sent, "
            "so count them through levy or add_heads in engine/primitives/levies.py"
        )
    print(f"raw head returns: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
