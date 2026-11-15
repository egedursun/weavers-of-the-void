import ast
import importlib
import types
import typing
from pathlib import Path

from pydantic import BaseModel

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
SHOWN = ("aerona.api.", "aerona.domain.models.")
KEYS = frozenset({"key", "value"})


def module_of(path: Path) -> str:
    return ".".join(("aerona", *path.relative_to(SOURCE).with_suffix("").parts))


def enum_text(node: ast.expr) -> bool:
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
