import importlib
import pkgutil
import re
from collections.abc import Mapping
from enum import Enum, StrEnum
from pathlib import Path

import aerona
from aerona.core.total import DECLARED_PARTIAL

SOURCE = Path(aerona.__file__).resolve().parent
SKIPPED = ("aerona.db.alembic", "aerona.migration", "aerona.services.books.pdf_worker")
NEAR_TOTAL = 0.75


def source_text() -> str:
    return "\n".join(path.read_text() for path in sorted(SOURCE.rglob("*.py")) if "alembic" not in path.parts)


def enum_tables() -> dict[int, tuple[str, str, Mapping[Enum, object]]]:
    found: dict[int, tuple[str, str, Mapping[Enum, object]]] = {}
    for info in pkgutil.walk_packages([str(SOURCE)], "aerona."):
        if info.name.startswith(SKIPPED):
            continue
        for name, value in vars(importlib.import_module(info.name)).items():
            if not name.isupper() or not isinstance(value, Mapping) or not value:
                continue
            keys = list(value)
            if isinstance(keys[0], Enum) and all(type(key) is type(keys[0]) for key in keys):
                found.setdefault(id(value), (info.name, name, value))
    return found


def test_a_near_total_enum_table_read_by_subscript_is_total_or_declares_what_it_leaves_out() -> None:
    text = source_text()
    gaps = []
    for table_id, (module, name, table) in sorted(enum_tables().items(), key=lambda item: item[1][:2]):
        kind = type(next(iter(table)))
        missing = sorted(member.value for member in kind if member not in table)
        if not missing or table_id in DECLARED_PARTIAL or len(table) < NEAR_TOTAL * len(kind) or not re.search(rf"\b{name}\[", text):
            continue
        gaps.append(f"{module}.{name} misses {kind.__name__} {missing}; fill it, or build it with partial(..., without=...)")
    assert gaps == [], "\n".join(gaps)


def enum_kinds() -> list[type[StrEnum]]:
    found: dict[str, type[StrEnum]] = {}
    for info in pkgutil.walk_packages([str(SOURCE)], "aerona."):
        if info.name.startswith(SKIPPED):
            continue
        for value in vars(importlib.import_module(info.name)).values():
            if isinstance(value, type) and issubclass(value, StrEnum) and value is not StrEnum and len(value) > 1:
                found.setdefault(f"{value.__module__}.{value.__qualname__}", value)
    return [found[key] for key in sorted(found)]


def text_tables() -> list[tuple[str, str, Mapping[str, object]]]:
    found: dict[int, tuple[str, str, Mapping[str, object]]] = {}
    for info in pkgutil.walk_packages([str(SOURCE)], "aerona."):
        if info.name.startswith(SKIPPED):
            continue
        for name, value in vars(importlib.import_module(info.name)).items():
            if name.isupper() and isinstance(value, Mapping) and value and all(type(key) is str for key in value):
                found.setdefault(id(value), (info.name, name, value))
    return sorted(found.values(), key=lambda item: item[:2])


def test_a_near_total_table_keyed_by_the_text_of_enum_values_is_total() -> None:
    text = source_text()
    kinds = enum_kinds()
    gaps = []
    for module, name, table in text_tables():
        if id(table) in DECLARED_PARTIAL or not re.search(rf"\b{name}\[", text):
            continue
        keys = set(table)
        if any(keys == {member.value for member in kind} for kind in kinds):
            continue
        for kind in kinds:
            values = {member.value for member in kind}
            if keys < values and len(keys) >= NEAR_TOTAL * len(values):
                gaps.append(f"{module}.{name} misses {kind.__name__} {sorted(values - keys)}; build it from the enum so every value has a row")
                break
    assert gaps == [], "\n".join(gaps)
