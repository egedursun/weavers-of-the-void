import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
HELPER = SOURCE / "engine" / "gods" / "essence.py"
CAPPING_CALLS = frozenset({"cap_gained_essence", "clamp_son"})
UNCAPPED_PURSES = frozenset({"creator", "foreign", "poorest", "tally"})


def raises_essence(node: ast.stmt) -> ast.Attribute | None:
    if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Attribute) and node.target.attr == "essence":
        return node.target
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        value = node.value
        if (
            isinstance(target, ast.Attribute)
            and target.attr == "essence"
            and isinstance(value, ast.BinOp)
            and isinstance(value.op, ast.Add)
            and isinstance(value.left, ast.Attribute)
            and value.left.attr == "essence"
        ):
            return target
    return None


def capped_next(body: list[ast.stmt], index: int) -> bool:
    if index + 1 >= len(body):
        return False
    after = body[index + 1]
    return isinstance(after, ast.Expr) and isinstance(after.value, ast.Call) and getattr(after.value.func, "id", "") in CAPPING_CALLS


def purse_name(target: ast.Attribute) -> str:
    base = target.value
    while isinstance(base, ast.Attribute):
        base = base.value
    return base.id if isinstance(base, ast.Name) else ""


def uncapped_gains() -> list[str]:
    found: list[str] = []
    for path in sorted(SOURCE.rglob("*.py")):
        if path == HELPER or "alembic" in path.parts or "migration" in path.parts:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            for field in ("body", "orelse", "finalbody"):
                body = getattr(node, field, None)
                if not isinstance(body, list):
                    continue
                for index, statement in enumerate(body):
                    target = raises_essence(statement)
                    if target is None or capped_next(body, index):
                        continue
                    if any(part in purse_name(target) for part in UNCAPPED_PURSES):
                        continue
                    found.append(f"{path.relative_to(SOURCE)}:{statement.lineno}")
    return found


def test_every_gain_of_a_son_essence_respects_its_cap() -> None:
    assert uncapped_gains() == []
