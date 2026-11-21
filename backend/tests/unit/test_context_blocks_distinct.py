import ast
from collections import Counter
from pathlib import Path

CONTEXT = Path(__file__).resolve().parents[2] / "src" / "aerona" / "agents" / "context"


def repeated_blocks(source: str) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Dict):
            continue
        calls = [
            value.value.func.id
            for key, value in zip(node.keys, node.values, strict=True)
            if isinstance(key, ast.Constant) and isinstance(value, ast.Await) and isinstance(value.value, ast.Call) and isinstance(value.value.func, ast.Name)
        ]
        found.extend(name for name, count in Counter(calls).items() if count > 1)
    return found


def test_no_context_block_is_filled_by_the_function_of_another() -> None:
    repeated = {path.name: repeated_blocks(path.read_text()) for path in sorted(CONTEXT.glob("*.py"))}
    assert {name: calls for name, calls in repeated.items() if calls} == {}


def test_a_block_filled_twice_by_one_function_is_caught() -> None:
    source = 'async def blocks():\n    return {"nature": await nature_lines(scope, me), "protected": await nature_lines(scope, me)}\n'
    assert repeated_blocks(source) == ["nature_lines"]
