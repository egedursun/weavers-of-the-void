import ast
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "src" / "aerona" / "engine"
DELTA_AND_NOTE = 4


def notes_written_by_the_engine() -> list[str]:
    found: list[str] = []
    for path in sorted(ENGINE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "change_relation"):
                continue
            if len(node.args) >= DELTA_AND_NOTE or any(keyword.arg == "note" for keyword in node.keywords):
                found.append(f"{path.relative_to(ENGINE)}:{node.lineno}")
    return found


def test_no_engine_step_overwrites_the_description_of_two_sons_bond() -> None:
    assert notes_written_by_the_engine() == []
