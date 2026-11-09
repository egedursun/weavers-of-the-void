import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENGINE = ROOT / "backend/src/aerona/engine"
DEPTH = ROOT / "frontend/src/features/wars/military/depth.ts"


def label_keys(table: str) -> set[str]:
    source = DEPTH.read_text(encoding="utf-8")
    body = re.search(rf"export const {table}: Record<string, Named> = \{{(.*?)\n\}}", source, re.DOTALL)
    assert body is not None, table
    return set(re.findall(r"^  '?(\w+)'?:", body.group(1), re.MULTILINE))


def subscripts(tree: ast.AST, name: str) -> set[str]:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            target = node.value
            if (isinstance(target, ast.Attribute) and target.attr == name) or (isinstance(target, ast.Name) and target.id == name):
                found.add(node.slice.value)
    return found


def dict_keys(tree: ast.AST, function: str, variable: str | None) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != function:
            continue
        for inner in ast.walk(node):
            value = None
            if (variable is None and isinstance(inner, ast.Return)) or (
                variable is not None and isinstance(inner, ast.Assign) and any(isinstance(item, ast.Name) and item.id == variable for item in inner.targets)
            ):
                value = inner.value
            if isinstance(value, ast.Dict):
                found |= {key.value for key in value.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)}
    return found


def trees() -> list[ast.AST]:
    return [ast.parse(path.read_text(encoding="utf-8")) for path in ENGINE.rglob("*.py")]


def test_every_morale_part_a_battle_records_has_a_label() -> None:
    parsed = trees()
    written = set().union(*(subscripts(tree, "morale_parts") | dict_keys(tree, "side_of", "parts") | subscripts_of_sheet(tree) for tree in parsed))
    assert {"divine", "god_shield", "terror_taken", "willpower"} <= written
    assert written - label_keys("MORALE_PART") == set()


def subscripts_of_sheet(tree: ast.AST) -> set[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "morale_sheet":
            return subscripts(node, "parts")
    return set()


def test_every_magic_part_a_battle_records_has_a_label() -> None:
    written = set().union(*(dict_keys(tree, "magic_sheet", None) for tree in trees()))
    assert {"god_struck", "god_spurned"} <= written
    assert written - label_keys("MAGIC_PART") == set()
