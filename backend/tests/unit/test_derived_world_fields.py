import ast
from enum import Enum
from pathlib import Path

from aerona.domain.enums import physics
from aerona.engine.cosmos.orbits import DERIVED_WORLD_FIELDS

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
SCANNED = ("engine", "services", "tools", "agents", "api")
WRITERS = frozenset(
    {
        "engine/cosmos/orbits.py:apply_to_world",
        "engine/cosmos/catastrophe.py:scorch_world",
        "engine/environment/control.py:set_world_calendar",
        "engine/environment/time_control.py:add_season",
        "engine/environment/time_control.py:remove_season",
        "engine/environment/time_control.py:set_moons",
        "engine/environment/time_control.py:release_calendar",
        "engine/phases/environment.py:ensure_world_calendar",
        "services/player/world_edits.py:_physics",
    }
)


def writes_of(path: Path) -> set[str]:
    found: set[str] = set()
    tree = ast.parse(path.read_text())
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for node in ast.walk(function):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AugAssign) else []
            named = any(isinstance(target, ast.Attribute) and target.attr in DERIVED_WORLD_FIELDS for target in targets)
            setter = (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "setattr"
                and len(node.args) > 1
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in DERIVED_WORLD_FIELDS
            )
            if named or setter:
                found.add(f"{path.relative_to(SOURCE).as_posix()}:{function.name}")
    return found


def test_only_the_heavens_and_holding_levers_write_what_the_heavens_derive() -> None:
    found = {site for folder in SCANNED for path in sorted((SOURCE / folder).rglob("*.py")) for site in writes_of(path)}
    assert found == WRITERS, (
        "a world value the heavens derive is written here; reshape the world's physics or hold the value in calendar_locked or locked, "
        f"then name the writer: {sorted(found ^ WRITERS)}"
    )


def test_every_value_of_the_heavens_is_produced_or_read_by_the_engine() -> None:
    engine = {node.attr for path in (SOURCE / "engine").rglob("*.py") for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.Attribute)}
    kinds: list[type[Enum]] = [
        value for value in vars(physics).values() if isinstance(value, type) and issubclass(value, Enum) and value.__module__ == physics.__name__
    ]
    unused = sorted(f"{kind.__name__}.{member.name}" for kind in kinds for member in kind if member.name not in engine)
    assert unused == []
