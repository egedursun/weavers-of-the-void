import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
STANDING = frozenset({"war_sides", "standing_sides"})


@dataclass(frozen=True)
class Standing:
    path: Path
    line: int
    function: str


def ended_column(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "ended_epoch" and isinstance(node.value, ast.Name) and node.value.id == "WarRow"


def reads_ended_wars(function: ast.AST) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Compare) and ended_column(node.left):
            if not all(isinstance(comparator, ast.Constant) and comparator.value is None for comparator in node.comparators):
                return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and ended_column(node.func.value)
            and node.func.attr in {"in_", "is_not", "isnot"}
        ):
            return True
    return False


def standing_calls(function: ast.AST) -> Iterator[ast.Call]:
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in STANDING:
            yield node


def standing_reads(files: dict[Path, str]) -> list[Standing]:
    found: list[Standing] = []
    for path, text in files.items():
        for function in ast.walk(ast.parse(text)):
            if isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef) and reads_ended_wars(function):
                found.extend(Standing(path, call.lineno, function.name) for call in standing_calls(function))
    return found


def main() -> int:
    found = standing_reads({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        where = f"{item.path.relative_to(ROOT)}:{item.line}"
        print(f"{where}: {item.function} reads ended wars but asks only for the sides still fighting; an ended war has none, use every_side")
    print(f"ended wars read through standing sides: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
