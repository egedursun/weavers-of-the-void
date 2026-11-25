import ast
import re
from collections.abc import Mapping
from enum import Enum, StrEnum
from functools import cache
from pathlib import Path

from aerona.core.total import DECLARED_PARTIAL
from tests.source_modules import SOURCE, source_modules

NEAR_TOTAL = 0.75


@cache
def source_texts() -> dict[Path, str]:
    return {path: path.read_text() for path in sorted(SOURCE.rglob("*.py")) if "alembic" not in path.parts}


def source_text() -> str:
    return "\n".join(source_texts().values())


@cache
def subscripted() -> frozenset[str]:
    return frozenset(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\[", source_text()))


def enum_tables() -> dict[int, tuple[str, str, Mapping[Enum, object]]]:
    found: dict[int, tuple[str, str, Mapping[Enum, object]]] = {}
    for module in source_modules():
        for name, value in vars(module).items():
            if not name.isupper() or not isinstance(value, Mapping) or not value:
                continue
            keys = list(value)
            if isinstance(keys[0], Enum) and all(type(key) is type(keys[0]) for key in keys):
                found.setdefault(id(value), (module.__name__, name, value))
    return found


def test_a_near_total_enum_table_read_by_subscript_is_total_or_declares_what_it_leaves_out() -> None:
    gaps = []
    for table_id, (module, name, table) in sorted(enum_tables().items(), key=lambda item: item[1][:2]):
        kind = type(next(iter(table)))
        missing = sorted(member.value for member in kind if member not in table)
        if not missing or table_id in DECLARED_PARTIAL or len(table) < NEAR_TOTAL * len(kind) or name not in subscripted():
            continue
        gaps.append(f"{module}.{name} misses {kind.__name__} {missing}; fill it, or build it with partial(..., without=...)")
    assert gaps == [], "\n".join(gaps)


def enum_kinds() -> list[type[StrEnum]]:
    found: dict[str, type[StrEnum]] = {}
    for module in source_modules():
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, StrEnum) and value is not StrEnum and len(value) > 1:
                found.setdefault(f"{value.__module__}.{value.__qualname__}", value)
    return [found[key] for key in sorted(found)]


def text_tables() -> list[tuple[str, str, Mapping[str, object]]]:
    found: dict[int, tuple[str, str, Mapping[str, object]]] = {}
    for module in source_modules():
        for name, value in vars(module).items():
            if name.isupper() and isinstance(value, Mapping) and value and all(type(key) is str for key in value):
                found.setdefault(id(value), (module.__name__, name, value))
    return sorted(found.values(), key=lambda item: item[:2])


def test_a_near_total_table_keyed_by_the_text_of_enum_values_is_total() -> None:
    kinds = [(kind, frozenset(member.value for member in kind)) for kind in enum_kinds()]
    gaps = []
    for module, name, table in text_tables():
        if id(table) in DECLARED_PARTIAL or name not in subscripted():
            continue
        keys = set(table)
        if any(keys == values for _kind, values in kinds):
            continue
        for kind, values in kinds:
            if keys < values and len(keys) >= NEAR_TOTAL * len(values):
                gaps.append(f"{module}.{name} misses {kind.__name__} {sorted(values - keys)}; build it from the enum so every value has a row")
                break
    assert gaps == [], "\n".join(gaps)


def enum_orders() -> dict[tuple[str, str], tuple[Enum, ...]]:
    found: dict[tuple[str, str], tuple[Enum, ...]] = {}
    for module in source_modules():
        for name, value in vars(module).items():
            if not name.isupper() or not isinstance(value, tuple) or len(value) < 2:
                continue
            if isinstance(value[0], Enum) and all(type(item) is type(value[0]) for item in value) and is_defined_in(module, name):
                found[(module.__name__, name)] = value
    return found


def is_defined_in(module: object, name: str) -> bool:
    path = getattr(module, "__file__", None)
    if path is None:
        return False
    text = source_texts().get(Path(path).resolve()) or Path(path).read_text()
    return re.search(rf"^{name}\b[^=\n]*=", text, re.MULTILINE) is not None


def readers_of(module: str, name: str) -> list[Path]:
    home = SOURCE.parent / Path(*module.split("."))
    files = [home.with_suffix(".py") if home.with_suffix(".py").exists() else home / "__init__.py"]
    imports = re.compile(rf"from {re.escape(module)} import [^\n]*\b{name}\b|from {re.escape(module)} import \([^)]*\b{name}\b", re.DOTALL)
    for path, text in source_texts().items():
        if path not in files and f"{name}.index(" in text and imports.search(text):
            files.append(path)
    return files


def unguarded_index_reads(module: str, name: str) -> list[str]:
    found: list[str] = []
    guard = re.compile(rf"\bin {name}\b")
    for path in readers_of(module, name):
        text = source_texts().get(path) or path.read_text()
        if f"{name}.index(" not in text:
            continue
        lines = text.splitlines()
        scopes = [node for node in ast.walk(ast.parse(text)) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))]
        for number, line in enumerate(lines, start=1):
            if f"{name}.index(" not in line:
                continue
            around = [node for node in scopes if node.lineno <= number <= (node.end_lineno or node.lineno)]
            scope = min(around, key=lambda node: (node.end_lineno or 0) - node.lineno, default=None)
            start = scope.lineno if scope is not None and not isinstance(scope, ast.Lambda) else number
            if not guard.search("\n".join(lines[start - 1 : number])):
                found.append(f"{path.relative_to(SOURCE)}:{number}")
    return found


def test_an_enum_order_read_by_index_holds_every_value_or_each_read_is_guarded() -> None:
    gaps = []
    for (module, name), order in sorted(enum_orders().items()):
        kind = type(order[0])
        missing = sorted(member.value for member in kind if member not in order)
        if not missing:
            continue
        for site in unguarded_index_reads(module, name):
            gaps.append(f"{site} reads {name}.index(...) but {name} misses {kind.__name__} {missing}; add them, or guard the read with `in {name}`")
    assert gaps == [], "\n".join(gaps)
