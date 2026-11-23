import ast
import dataclasses
from pathlib import Path

from aerona.rules.model import RULE_METADATA_KEY
from aerona.rules.registry import Rules

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "aerona"
RULE_HOLDERS = ("rules.", "table.", "settings.")


def rule_labels() -> dict[str, list[str]]:
    labels: dict[str, list[str]] = {}
    rules = Rules()
    for namespace in dataclasses.fields(rules):
        table = getattr(rules, namespace.name)
        if not dataclasses.is_dataclass(table):
            continue
        for item in dataclasses.fields(table):
            meta = item.metadata.get(RULE_METADATA_KEY)
            if meta is not None:
                labels.setdefault(item.name, []).append(meta.label)
    return labels


LABELS = rule_labels()


def is_percent(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == "PERCENT"


def factors(node: ast.expr) -> list[ast.expr]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Div)):
        return factors(node.left) + (factors(node.right) if isinstance(node.op, ast.Mult) else [])
    return [node]


def shares_of(function: ast.AST) -> set[str]:
    seen: dict[str, bool] = {}
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            pairs = (
                list(zip(target.elts, node.value.elts, strict=False))
                if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple)
                else [(target, node.value)]
            )
            for name, value in pairs:
                if isinstance(name, ast.Name):
                    divided = isinstance(value, ast.BinOp) and isinstance(value.op, ast.Div) and is_percent(value.right)
                    seen[name.id] = seen.get(name.id, True) and divided
    return {name for name, divided in seen.items() if divided}


def is_amount(node: ast.expr) -> bool:
    if not isinstance(node, ast.Attribute) or node.attr not in LABELS:
        return False
    chain = ast.unparse(node)
    held_by_rules = ".rules." in f".{chain}" or chain.startswith(RULE_HOLDERS)
    return held_by_rules and all("%" not in label for label in LABELS[node.attr])


def rescaled(source: str) -> list[str]:
    found: list[str] = []
    for function in ast.walk(ast.parse(source)):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        shares = shares_of(function)
        for node in ast.walk(function):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and is_percent(node.right):
                parts = factors(node.left)
                if any(isinstance(part, ast.Name) and part.id in shares for part in parts) and any(is_amount(part) for part in parts):
                    found.append(f"{node.lineno}: {ast.unparse(node)}")
    return found


def test_an_amount_rule_on_a_share_is_never_divided_by_percent_again() -> None:
    old = "def change(land, ctx):\n    grazed = land.grazed / PERCENT\n    return grazed * ctx.rules.soils.leached_amend_gain / PERCENT\n"
    assert rescaled(old) != []
    assert rescaled(old.replace("leached_amend_gain / PERCENT", "leached_amend_gain")) == []
    wrong = [
        f"{path.relative_to(SOURCE_ROOT)}:{line}"
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        if "__pycache__" not in path.parts
        for line in rescaled(path.read_text(encoding="utf-8"))
    ]
    assert wrong == []
