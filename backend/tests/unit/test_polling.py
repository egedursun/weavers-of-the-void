import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]


def sleeps(node: ast.AST) -> bool:
    return any(
        isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute) and item.func.attr == "sleep" and ast.unparse(item.func.value) == "asyncio"
        for item in ast.walk(node)
    )


def counted(loop: ast.For) -> bool:
    return isinstance(loop.iter, ast.Call) and isinstance(loop.iter.func, ast.Name) and loop.iter.func.id == "range"


def test_a_test_waits_by_a_deadline_never_by_a_count_of_sleeps() -> None:
    found = [
        f"{path.relative_to(TESTS)}:{node.lineno}"
        for path in sorted(TESTS.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, (ast.For, ast.AsyncFor)) and counted(node) and sleeps(node)
    ]
    assert not found, f"wait with tests.polling.until, which keeps a deadline, so a loaded machine never fails a test: {found}"
