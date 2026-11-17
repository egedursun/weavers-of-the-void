import ast
import importlib
from enum import Enum
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
ENUMS = SOURCE / "domain" / "enums"


def enum_classes() -> dict[str, type[Enum]]:
    found: dict[str, type[Enum]] = {}
    for path in sorted(ENUMS.glob("*.py")):
        module = importlib.import_module(f"aerona.domain.enums.{path.stem}")
        for name, value in vars(module).items():
            if isinstance(value, type) and issubclass(value, Enum) and value.__module__ == module.__name__:
                found[name] = value
    return found


def keyed_enum(node: ast.Dict) -> tuple[str, set[str]] | None:
    owners: set[str] = set()
    members: set[str] = set()
    for key in node.keys:
        if not (isinstance(key, ast.Attribute) and isinstance(key.value, ast.Name)):
            return None
        owners.add(key.value.id)
        members.add(key.attr)
    return (owners.pop(), members) if len(owners) == 1 and members else None


def partial_inline_reads(text: str, classes: dict[str, type[Enum]]) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Dict) and not isinstance(node.slice, ast.Constant):
            keyed = keyed_enum(node.value)
            if keyed is None or keyed[0] not in classes:
                continue
            missing = {member.name for member in classes[keyed[0]]} - keyed[1]
            if missing:
                found.append(f"{node.lineno}: {keyed[0]} misses {sorted(missing)}")
    return found


def test_an_inline_table_that_leaves_out_values_is_found() -> None:
    classes = {"Colour": Enum("Colour", ["RED", "BLUE", "GREEN"])}
    assert partial_inline_reads("x = {Colour.RED: 1, Colour.BLUE: 2}[kind]", classes) == ["1: Colour misses ['GREEN']"]
    assert partial_inline_reads("x = {Colour.RED: 1, Colour.BLUE: 2, Colour.GREEN: 3}[kind]", classes) == []


def test_no_inline_table_read_by_an_enum_value_leaves_out_values() -> None:
    classes = enum_classes()
    found = [
        f"{path.relative_to(SOURCE)}:{item}"
        for path in sorted(SOURCE.rglob("*.py"))
        for item in partial_inline_reads(path.read_text(encoding="utf-8"), classes)
    ]
    assert found == []
