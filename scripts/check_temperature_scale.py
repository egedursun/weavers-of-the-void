import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
SCALED = frozenset({"temperature"})
FLOOR = 0
CEILING = 100
BELOW = (ast.Lt, ast.LtE)
ABOVE = (ast.Gt, ast.GtE)


@dataclass(frozen=True)
class Reading:
    path: Path
    line: int
    text: str


def number(node: ast.AST) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = number(node.operand)
        return -inner if inner is not None else None
    return None


def scaled(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr in SCALED


def impossible(left: ast.AST, op: ast.cmpop, right: ast.AST) -> bool:
    value = number(right)
    if not scaled(left) or value is None:
        return False
    return (isinstance(op, BELOW) and value <= FLOOR and not (isinstance(op, ast.LtE) and value == FLOOR)) or (
        isinstance(op, ABOVE) and value >= CEILING and not (isinstance(op, ast.GtE) and value == CEILING)
    )


def readings(files: dict[Path, str]) -> list[Reading]:
    found: list[Reading] = []
    for path, text in files.items():
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Compare):
                continue
            operands = [node.left, *node.comparators]
            for index, op in enumerate(node.ops):
                if impossible(operands[index], op, operands[index + 1]):
                    found.append(Reading(path, node.lineno, ast.unparse(node)))
    return found


def main() -> int:
    found = readings({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} compares a temperature outside its 0 to 100 scale; read the temperature band")
    print(f"impossible temperature readings: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
