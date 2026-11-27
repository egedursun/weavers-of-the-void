import ast
from pathlib import Path

from aerona.db.fixups import MARKER_PREFIXES

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"


def module_constants(tree: ast.Module) -> dict[str, str]:
    found: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node.value.value
    return found


def test_every_first_sight_family_is_a_known_marker() -> None:
    unknown: list[str] = []
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        constants = module_constants(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "first_sight" and len(node.args) >= 2:
                family = node.args[1]
                value = constants.get(family.id) if isinstance(family, ast.Name) else family.value if isinstance(family, ast.Constant) else None
                if not isinstance(value, str) or not f"{value}.".startswith(MARKER_PREFIXES):
                    unknown.append(f"{path.relative_to(SOURCE)}:{node.lineno}")
    assert unknown == []
