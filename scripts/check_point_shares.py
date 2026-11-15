import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
POINT_STATS = frozenset({"wealth", "prosperity"})
READERS = frozenset({"stat", "stat_or"})
AMOUNTS = frozenset({"stake", "amount", "price", "cost", "fee", "levy", "spend", "bribe", "ransom", "wage", "rent"})


@dataclass(frozen=True)
class Share:
    path: Path
    line: int
    text: str


def reads_points(node: ast.AST) -> bool:
    for item in ast.walk(node):
        if isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id in READERS:
            if any(isinstance(arg, ast.Constant) and arg.value in POINT_STATS for arg in item.args):
                return True
    return False


def scaled(node: ast.AST) -> bool:
    return any(isinstance(item, ast.BinOp) and isinstance(item.op, (ast.Mult, ast.Div, ast.FloorDiv)) for item in ast.walk(node))


def tainted_names(function: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and reads_points(node.value):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return names


def uses(node: ast.AST, names: set[str]) -> bool:
    return any(isinstance(item, ast.Name) and item.id in names for item in ast.walk(node))


def point_shares(tree: ast.AST) -> Iterator[ast.Assign]:
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        tainted = tainted_names(function)
        for node in ast.walk(function):
            if not isinstance(node, ast.Assign) or not scaled(node.value):
                continue
            if not (reads_points(node.value) or uses(node.value, tainted)):
                continue
            if any(isinstance(target, ast.Name) and target.id in AMOUNTS for target in node.targets):
                yield node


def raw_shares(files: dict[Path, str]) -> list[Share]:
    return sorted(
        (Share(path, node.lineno, ast.unparse(node)) for path, text in files.items() for node in point_shares(ast.parse(text))),
        key=lambda item: (str(item.path), item.line),
    )


def main() -> int:
    found = raw_shares({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} takes an amount of coin as a share of a 0 to 100 point stat, which rounds to "
            "nothing; take it from coin_of and move it with take_coin and give_coin"
        )
    print(f"point shares: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
