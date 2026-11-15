import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
SIMPLE = (ast.Assign, ast.AugAssign, ast.Expr, ast.Return, ast.AnnAssign)
READS_FEAR = ("fear", "dread", "resist(")


@dataclass(frozen=True)
class Loss:
    path: Path
    line: int
    text: str


def morale_attribute(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "morale"


def lowers_morale(statement: ast.stmt) -> bool:
    for node in ast.walk(statement):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub) and morale_attribute(node.left):
            return True
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Sub) and morale_attribute(node.target):
            return True
        if (
            isinstance(node, ast.Call)
            and len(node.args) >= 3
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "morale"
            and isinstance(node.args[2], ast.UnaryOp)
            and isinstance(node.args[2].op, ast.USub)
        ):
            return True
    return False


def losses(files: dict[Path, str]) -> list[Loss]:
    found: list[Loss] = []
    for path, text in files.items():
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, SIMPLE) and lowers_morale(node):
                told = ast.unparse(node)
                if not any(token in told for token in READS_FEAR):
                    found.append(Loss(path, node.lineno, told))
    return found


def main() -> int:
    found = losses({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} lowers morale without the fear of the body; scale it by fear_of from engine/body/variants.py")
    print(f"morale losses: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
