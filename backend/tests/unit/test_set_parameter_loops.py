import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
CHECKED = ("engine", "catalog")
SET_TYPES = frozenset({"frozenset", "set", "AbstractSet", "Set"})


def set_parameters(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    arguments = [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs]
    return {item.arg for item in arguments if item.annotation is not None and ast.unparse(item.annotation).split("[")[0] in SET_TYPES}


def unsorted_loops(text: str) -> list[int]:
    found: list[int] = []
    for function in ast.walk(ast.parse(text)):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        names = set_parameters(function)
        for node in ast.walk(function):
            if isinstance(node, (ast.For, ast.AsyncFor)):
                sources = [node.iter]
            elif isinstance(node, (ast.ListComp, ast.DictComp, ast.GeneratorExp)):
                sources = [generator.iter for generator in node.generators]
            else:
                sources = []
            found.extend(node.lineno for source in sources if isinstance(source, ast.Name) and source.id in names)
    return sorted(set(found))


def test_a_loop_over_a_set_parameter_in_its_hash_order_is_found() -> None:
    text = (
        "def fastest(modes: frozenset[int]) -> int:\n    return max(mode for mode in modes)\n\n\n"
        "def kept(modes: frozenset[int]) -> int:\n    return max(mode for mode in sorted(modes))\n"
    )
    assert unsorted_loops(text) == [2]


def test_no_engine_or_catalogue_loop_walks_a_set_parameter_in_its_hash_order() -> None:
    found = [
        f"{path.relative_to(SOURCE)}:{line}"
        for folder in CHECKED
        for path in sorted((SOURCE / folder).rglob("*.py"))
        for line in unsorted_loops(path.read_text(encoding="utf-8"))
    ]
    assert found == []
