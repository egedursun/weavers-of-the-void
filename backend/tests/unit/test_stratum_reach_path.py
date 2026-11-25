import ast
from pathlib import Path

import aerona

SOURCE = Path(aerona.__file__).resolve().parent
REACHERS = {("engine/environment/deep.py", "reach_stratum"), ("engine/environment/deep.py", "reach_layer"), ("engine/environment/deep.py", "breach")}
MARKS = frozenset({"reached_epoch", "breached_epoch"})


def writers() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path in sorted(SOURCE.rglob("*.py")):
        if "alembic" in path.parts or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(SOURCE).as_posix()
        for function in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(function):
                if not isinstance(node, ast.Assign) or (isinstance(node.value, ast.Constant) and node.value.value is None):
                    continue
                if any(isinstance(target, ast.Attribute) and target.attr in MARKS for target in node.targets):
                    found.add((relative, function.name))
    return found


def test_a_stratum_is_reached_or_breached_only_through_the_one_path_that_tells_it_and_opens_its_way_down() -> None:
    assert writers() - REACHERS == set(), "reach a stratum through reach_stratum in engine/environment/deep.py"
