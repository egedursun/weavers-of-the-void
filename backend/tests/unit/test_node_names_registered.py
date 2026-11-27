import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "aerona"
SCANNED = ("engine", "tools", "agents", "services")
NODE_HOLDERS = frozenset({"mortal", "entity", "being", "child", "hero", "node", "realm", "town", "settlement", "people", "dead", "bearer"})
KEEPERS = frozenset({ROOT / "engine" / "primitives" / "renames.py"})


def holder_of(target: ast.expr) -> str | None:
    if not isinstance(target, ast.Attribute) or target.attr != "name":
        return None
    owner = target.value
    if isinstance(owner, ast.Name):
        return owner.id
    if isinstance(owner, ast.Attribute):
        return owner.attr
    return None


def unregistered_renames() -> list[str]:
    found: list[str] = []
    for folder in SCANNED:
        for path in sorted((ROOT / folder).rglob("*.py")):
            if path in KEEPERS:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                targets: list[ast.expr] = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
                found.extend(f"{path.relative_to(ROOT)}:{target.lineno}" for target in targets if holder_of(target) in NODE_HOLDERS)
    return found


def test_a_node_is_renamed_only_through_the_name_register() -> None:
    assert unregistered_renames() == []
