import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
FIELD = "treasury"
SHARES = (ast.Mult, ast.FloorDiv, ast.Div)


@dataclass(frozen=True)
class Share:
    path: Path
    line: int
    text: str


def bare(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == FIELD


def taken(node: ast.AST) -> bool:
    if isinstance(node, ast.BinOp):
        return isinstance(node.op, SHARES) and (bare(node.left) or bare(node.right))
    if isinstance(node, ast.Call):
        return isinstance(node.func, ast.Name) and node.func.id == "min" and any(bare(argument) for argument in node.args)
    return False


def shares(files: dict[Path, str]) -> list[Share]:
    found: list[Share] = []
    for path, text in files.items():
        for node in ast.walk(ast.parse(text)):
            if taken(node):
                found.append(Share(path, getattr(node, "lineno", 0), ast.unparse(node)))
    return found


def main() -> int:
    found = shares({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} takes a share of a treasury that may be in debt; read it through held_coin")
    print(f"treasury shares: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
