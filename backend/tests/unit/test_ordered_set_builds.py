import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"


def set_constants(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
            continue
        value = node.value
        is_set = isinstance(value, (ast.Set, ast.SetComp)) or (isinstance(value, ast.Call) and getattr(value.func, "id", "") in ("frozenset", "set"))
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names |= {target.id for target in targets if is_set and isinstance(target, ast.Name)}
    return names


def unordered_builds(text: str) -> list[int]:
    tree = ast.parse(text)
    sets = set_constants(tree)
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, (ast.ListComp, ast.DictComp))
        for generator in node.generators
        if isinstance(generator.iter, ast.Name) and generator.iter.id in sets
    ]


def test_a_list_or_dict_built_from_a_set_in_its_hash_order_is_found() -> None:
    text = "WATER = frozenset({1, 2})\nfit = {kind: 80 for kind in WATER}\nkept = {kind: 80 for kind in sorted(WATER)}\n"
    assert unordered_builds(text) == [2]


def test_no_stored_list_or_dict_is_built_in_the_hash_order_of_a_set() -> None:
    found = [f"{path.relative_to(SOURCE)}:{line}" for path in sorted(SOURCE.rglob("*.py")) for line in unordered_builds(path.read_text(encoding="utf-8"))]
    assert found == []
