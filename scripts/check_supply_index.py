import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
INDEX_CALLS = frozenset({"stock", "supply_index", "fed_index"})
HEAD_CALLS = frozenset({"headcount", "population_of"})
STAT_CALLS = frozenset({"stat", "stat_or"})
HEAD_NAMES = frozenset({"population", "people"})
SCALING = (ast.Mult, ast.Div, ast.FloorDiv)
SHIFT_CALLS = frozenset({"shift_stock", "move_stock"})


@dataclass(frozen=True)
class Rescaled:
    path: Path
    line: int
    text: str


def called(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None


def headcount_in(node: ast.AST) -> bool:
    for item in ast.walk(node):
        name = called(item)
        if name in HEAD_CALLS:
            return True
        if name in STAT_CALLS and isinstance(item, ast.Call) and any(isinstance(arg, ast.Constant) and arg.value == "population" for arg in item.args):
            return True
        if isinstance(item, ast.Name) and item.id in HEAD_NAMES:
            return True
    return False


def index_in(node: ast.AST, names: set[str]) -> bool:
    return any(called(item) in INDEX_CALLS or (isinstance(item, ast.Name) and item.id in names) for item in ast.walk(node))


def index_names(function: ast.AST) -> set[str]:
    found: set[str] = set()
    while True:
        grown = set(found)
        for node in ast.walk(function):
            if isinstance(node, ast.Assign) and index_in(node.value, found) and not headcount_in(node.value):
                grown |= {target.id for target in node.targets if isinstance(target, ast.Name)}
            if isinstance(node, ast.AnnAssign) and node.value is not None and index_in(node.value, found) and isinstance(node.target, ast.Name):
                grown.add(node.target.id)
            if isinstance(node, ast.AugAssign) and index_in(node.value, found) and isinstance(node.target, ast.Name):
                grown.add(node.target.id)
        if grown == found:
            return found
        found = grown


def headcount_names(function: ast.AST) -> set[str]:
    return {
        target.id
        for node in ast.walk(function)
        if isinstance(node, ast.Assign) and headcount_in(node.value)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


def counted_in(node: ast.AST, names: set[str]) -> bool:
    return headcount_in(node) or any(isinstance(item, ast.Name) and item.id in names for item in ast.walk(node))


def sides_of(node: ast.AST) -> list[ast.AST] | None:
    if called(node) in SHIFT_CALLS and isinstance(node, ast.Call):
        return [node, *node.args, *(keyword.value for keyword in node.keywords)]
    if isinstance(node, ast.BinOp) and isinstance(node.op, SCALING):
        return [node.left, node.right]
    if isinstance(node, ast.Compare):
        return [node.left, *node.comparators]
    return None


def rescaled(files: dict[Path, str]) -> list[Rescaled]:
    found: list[Rescaled] = []
    for path, text in files.items():
        for function in ast.walk(ast.parse(text)):
            if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            names = index_names(function)
            heads = headcount_names(function)
            for node in ast.walk(function):
                sides = sides_of(node)
                if sides is None or not isinstance(node, ast.expr):
                    continue
                indexed = sides[:1] if called(node) in SHIFT_CALLS else [side for side in sides if index_in(side, names)]
                counted = (
                    [side for side in sides[1:] if counted_in(side, heads)]
                    if called(node) in SHIFT_CALLS
                    else [side for side in sides if headcount_in(side) and not index_in(side, names)]
                )
                if indexed and counted:
                    found.append(Rescaled(path, node.lineno, ast.unparse(node)))
    return sorted(set(found), key=lambda item: (str(item.path), item.line))


def main() -> int:
    found = rescaled({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} scales a supply index by a headcount; "
            "the index already stands for the community's own needs (100 = one epoch), so compare or move it as it is"
        )
    print(f"supply index rescaled by population: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
