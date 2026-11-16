import ast
import importlib
import inspect
from collections.abc import Iterator
from pathlib import Path
from typing import get_type_hints

from pydantic import BaseModel

from aerona.services import player

PLAYER = Path(player.__file__).parent


def iterated_names(function: ast.AsyncFunctionDef | ast.FunctionDef) -> Iterator[ast.expr]:
    for node in ast.walk(function):
        loops = (
            [node] if isinstance(node, ast.For) else node.generators if isinstance(node, ast.ListComp | ast.GeneratorExp | ast.SetComp | ast.DictComp) else []
        )
        for loop in loops:
            target, source = loop.target, loop.iter
            if not isinstance(target, ast.Name):
                continue
            body = ast.walk(node)
            reads = any(
                isinstance(item, ast.Call)
                and isinstance(item.func, ast.Name)
                and item.func.id == "getattr"
                and len(item.args) >= 2
                and isinstance(item.args[0], ast.Name)
                and item.args[0].id == "command"
                and isinstance(item.args[1], ast.Name)
                and item.args[1].id == target.id
                for item in body
            )
            if reads:
                yield source


def names_of(module: object, source: ast.expr) -> list[str]:
    try:
        value = eval(compile(ast.Expression(source), "<names>", "eval"), vars(module))
    except Exception:
        return []
    return [name for name in value if isinstance(name, str)] if isinstance(value, tuple | list | frozenset | set) else []


def test_every_name_a_lever_reads_from_its_command_is_a_field_of_that_command() -> None:
    missing: list[str] = []
    for path in sorted(PLAYER.glob("*.py")):
        module = importlib.import_module(f"aerona.services.player.{path.stem}")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in [node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)]:
            handler = getattr(module, function.name, None)
            if handler is None or not callable(handler):
                continue
            hints = get_type_hints(inspect.unwrap(handler)) if inspect.isfunction(inspect.unwrap(handler)) else {}
            command = hints.get("command")
            if not (inspect.isclass(command) and issubclass(command, BaseModel)):
                continue
            for source in iterated_names(function):
                missing += [
                    f"{path.stem}.{function.name}: {command.__name__} lacks {name}" for name in names_of(module, source) if name not in command.model_fields
                ]
    assert missing == []
