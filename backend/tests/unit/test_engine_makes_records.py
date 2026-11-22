import ast
import importlib
import inspect
import pkgutil
import re
import textwrap
from collections.abc import Callable, Iterable, Mapping
from functools import cache, partial
from typing import Any

import aerona.tools
from aerona.db.base import Base
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.pipeline import all_phases

REACHED_PACKAGES = ("aerona.engine", "aerona.tools")
DISPATCH_DEPTH = 3


def body(function: Callable[..., Any]) -> str:
    try:
        return textwrap.dedent(inspect.getsource(function))
    except (OSError, TypeError):
        return ""


def followed(value: object, depth: int = 0) -> list[Callable[..., Any]]:
    if isinstance(value, Mapping) and depth < DISPATCH_DEPTH:
        return [target for item in (*value.keys(), *value.values()) for target in followed(item, depth + 1)]
    if isinstance(value, tuple | list | frozenset | set) and depth < DISPATCH_DEPTH:
        return [target for item in value for target in followed(item, depth + 1)]
    if isinstance(value, partial):
        return followed(value.func, depth)
    target = inspect.unwrap(value) if callable(value) else None
    named = inspect.isfunction(target) and target.__name__ != "<lambda>"
    return [target] if named and target.__module__.startswith(REACHED_PACKAGES) else []


def callees(function: Callable[..., Any]) -> list[Callable[..., Any]]:
    module = inspect.getmodule(function)
    found: list[Callable[..., Any]] = []
    for node in ast.walk(ast.parse(body(function) or "pass")):
        named = getattr(module, node.id, None) if isinstance(node, ast.Name) else None
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and inspect.ismodule(getattr(module, node.value.id, None)):
            named = getattr(getattr(module, node.value.id), node.attr, None)
        found.extend(followed(named))
    return found


def reached(roots: Iterable[Callable[..., Any]]) -> str:
    seen: set[Callable[..., Any]] = set()
    stack = [inspect.unwrap(root) for root in roots]
    while stack:
        function = stack.pop()
        if function not in seen:
            seen.add(function)
            stack.extend(callees(function))
    return "\n".join(body(function) for function in seen)


def tool_functions() -> list[Callable[..., Any]]:
    found: list[Callable[..., Any]] = []
    for info in pkgutil.walk_packages(aerona.tools.__path__, "aerona.tools."):
        module = importlib.import_module(info.name)
        found.extend(member for _, member in inspect.getmembers(module, inspect.isfunction) if member.__module__ == module.__name__)
    return found


@cache
def stepped_text() -> str:
    return reached(phase.run for phase in all_phases())


@cache
def tooled_text() -> str:
    return reached(tool_functions())


def constructs(text: str, name: str) -> bool:
    return f"{name}(" in text and re.search(rf"\b{name}\(", text) is not None


def idle_records(tables: dict[str, list[str]], classes: dict[str, str], *, stepped: Callable[[str], bool], tooled: Callable[[str], bool]) -> list[str]:
    return [
        f"{key}: {table} is made by an agent tool but by no engine step"
        for key, names in tables.items()
        for table in names
        if (name := classes.get(table)) is not None and tooled(name) and not stepped(name)
    ]


def test_the_engine_itself_makes_the_records_of_every_mechanic_the_model_can_make() -> None:
    classes = {table.name: mapper.class_.__name__ for mapper in Base.registry.mappers for table in mapper.tables}
    tables = {mechanic.key: list(mechanic.tables) for mechanic in REGISTERED.values()}
    found = idle_records(tables, classes, stepped=lambda name: constructs(stepped_text(), name), tooled=lambda name: constructs(tooled_text(), name))
    assert found == []


def test_a_record_only_a_tool_reaches_is_caught() -> None:
    classes = {"wave_warnings": "WaveWarningRow", "sea_waves": "SeaWaveRow"}
    tables = {"sea_waves": ["sea_waves", "wave_warnings"]}
    found = idle_records(tables, classes, stepped=lambda name: name == "SeaWaveRow", tooled=lambda name: True)
    assert found == ["sea_waves: wave_warnings is made by an agent tool but by no engine step"]
    assert constructs("row = WaveWarningRow(region_entity_id=1)", "WaveWarningRow") and not constructs("SeaWaveWarningRow()", "WaveWarningRow")
