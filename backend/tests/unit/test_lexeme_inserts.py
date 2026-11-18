import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"


def guarded(call: ast.Call, parents: dict[ast.AST, ast.AST]) -> bool:
    node: ast.AST | None = parents.get(call)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add_lexeme":
        return True
    while node is not None and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        node = parents.get(node)
    return node is not None and any(isinstance(item, ast.Name) and item.id == "lexeme_key" for item in ast.walk(node))


def test_every_word_enters_a_tongue_through_one_door_that_knows_its_words() -> None:
    loose: list[str] = []
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text())
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "LexemeRow" and not guarded(node, parents):
                loose.append(f"{path.relative_to(SOURCE)}:{node.lineno}")
    assert not loose, f"add words through add_lexeme so a word a tongue already has is kept, not added twice: {loose}"
