import ast
import importlib
import types
import typing
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import String, Text

from aerona.db import tables
from aerona.db.base import Base

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
SHOWN = ("aerona.api.", "aerona.domain.models.")
KEYS = frozenset({"key", "value"})


def module_of(path: Path) -> str:
    return ".".join(("aerona", *path.relative_to(SOURCE).with_suffix("").parts))


def literal_fields() -> frozenset[str]:
    found: set[str] = set()
    for path in sorted((SOURCE / "domain" / "models").rglob("*.py")):
        module = importlib.import_module(module_of(path))
        for value in vars(module).values():
            if not (isinstance(value, type) and issubclass(value, BaseModel)):
                continue
            for name, field in value.model_fields.items():
                parts = typing.get_args(field.annotation) if typing.get_origin(field.annotation) in {typing.Union, types.UnionType} else (field.annotation,)
                if any(typing.get_origin(part) is typing.Literal and len(typing.get_args(part)) > 1 for part in parts):
                    found.add(name)
    return frozenset(found)


LITERAL_FIELDS = literal_fields()


def literal_read(node: ast.expr) -> bool:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr" and len(node.args) >= 2:
        name = node.args[1]
        return isinstance(name, ast.Constant) and name.value in LITERAL_FIELDS
    return isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) and node.value.attr == "stats" and node.attr in LITERAL_FIELDS


def enum_text(node: ast.expr) -> bool:
    if literal_read(node):
        return True
    if isinstance(node, ast.IfExp):
        return enum_text(node.body) or enum_text(node.orelse)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return enum_text(node.func.value)
    if isinstance(node, ast.Attribute):
        return node.attr == "value" or enum_text(node.value)
    return False


def plain_text(annotation: object) -> bool:
    parts = typing.get_args(annotation) if isinstance(annotation, types.UnionType) or typing.get_origin(annotation) is typing.Union else (annotation,)
    return str in parts and set(parts) <= {str, type(None)}


def shown_models(tree: ast.Module, module: str) -> dict[str, str]:
    found = {node.name: module for node in tree.body if isinstance(node, ast.ClassDef)} if module.startswith(SHOWN) else {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(SHOWN):
            found.update({alias.asname or alias.name: node.module for alias in node.names})
    return found


def text_fed_by_enums(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    models = shown_models(tree, module_of(path))
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in models):
            continue
        model = getattr(importlib.import_module(models[node.func.id]), node.func.id, None)
        if not (isinstance(model, type) and issubclass(model, BaseModel)):
            continue
        for keyword in node.keywords:
            field = model.model_fields.get(keyword.arg or "")
            if field is None or not plain_text(field.annotation) or not enum_text(keyword.value):
                continue
            if keyword.arg in KEYS and "label" in model.model_fields:
                continue
            found.append(f"{path.relative_to(SOURCE)}:{node.lineno} {model.__name__}.{keyword.arg}")
    return found


def test_a_shown_record_types_every_enum_it_carries() -> None:
    found = [line for path in sorted(SOURCE.rglob("*.py")) if "alembic" not in path.parts for line in text_fed_by_enums(path)]
    assert found == [], f"type these fields with their enum so every screen labels them: {found}"


SHOWN_TEXT = frozenset({"text", "summary", "description", "note", "body", "account", "story", "narrative", "title", "caption", "line", "reason", "label"})


def row_text_columns() -> dict[str, frozenset[str]]:
    assert tables
    found: dict[str, frozenset[str]] = {}
    for mapper in Base.registry.mappers:
        columns = mapper.columns
        found[mapper.class_.__name__] = frozenset(
            column.key
            for column in columns
            if column.key in SHOWN_TEXT and isinstance(column.type, (String, Text)) and getattr(column.type, "enum_class", None) is None
        )
    return found


def rows_fed_by_enums(path: Path, texts: dict[str, frozenset[str]]) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in texts):
            continue
        found.extend(
            f"{path.relative_to(SOURCE)}:{node.lineno} {node.func.id}.{keyword.arg}"
            for keyword in node.keywords
            if keyword.arg in texts[node.func.id] and enum_text(keyword.value)
        )
    return found


def test_a_stored_text_column_never_holds_an_enum_value() -> None:
    texts = row_text_columns()
    found = [line for path in sorted(SOURCE.rglob("*.py")) if "alembic" not in path.parts for line in rows_fed_by_enums(path, texts)]
    assert found == [], f"keep the enum in a typed column and tell it as a line, never store its raw value as text: {found}"


PASSED_TEXT = SHOWN_TEXT - {"label", "title"}


def calls_fed_by_enums(path: Path) -> list[str]:
    return [
        f"{path.relative_to(SOURCE)}:{node.lineno} {keyword.arg}"
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg in PASSED_TEXT and enum_text(keyword.value)
    ]


def test_no_call_hands_on_an_enum_value_as_shown_text() -> None:
    found = [line for path in sorted(SOURCE.rglob("*.py")) if "alembic" not in path.parts for line in calls_fed_by_enums(path)]
    assert found == [], f"pass the enum through spoken() or its label, never its raw value as a note, reason or line: {found}"
