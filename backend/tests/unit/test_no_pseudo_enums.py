import ast
import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
KEY = re.compile(r"^[a-z][a-z0-9_]*$")
LEAST = 3


def pseudo_enums(text: str) -> list[str]:
    found: list[str] = []
    for node in ast.parse(text).body:
        if not isinstance(node, ast.ClassDef) or node.bases:
            continue
        values = [
            statement.value.value
            for statement in node.body
            if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str)
        ]
        if len(values) >= LEAST and len(values) == len(node.body) and all(KEY.match(value) for value in values):
            found.append(node.name)
    return found


def test_a_class_of_keys_is_a_string_enum() -> None:
    offenders = [f"{path.relative_to(SOURCE)}: {name}" for path in sorted(SOURCE.rglob("*.py")) for name in pseudo_enums(path.read_text(encoding="utf-8"))]
    assert offenders == []


def test_the_rule_catches_a_class_of_keys() -> None:
    assert pseudo_enums('class Mood:\n    A = "blood_shed"\n    B = "wars"\n    C = "leak"\n') == ["Mood"]
    assert pseudo_enums('class Words:\n    A = "is located in"\n    B = "speaks"\n    C = "worships"\n') == []
