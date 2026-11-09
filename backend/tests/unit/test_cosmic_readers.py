import ast
import dataclasses
from enum import Enum
from functools import cache
from pathlib import Path

import pytest

import aerona
from aerona.domain.enums.cosmography import PhenomenonCause, RiftCause
from aerona.engine.cosmos import kinds
from aerona.engine.cosmos.placement import CosmicPull

SOURCE = Path(aerona.__file__).resolve().parent
KINDS = Path(kinds.__file__).resolve()
PLACEMENT = SOURCE / "engine" / "cosmos" / "placement.py"
PRODUCERS = ("engine", "services", "tools", "agents")
MECHANICS = sorted(
    (value for value in vars(kinds).values() if isinstance(value, type) and dataclasses.is_dataclass(value) and value.__name__.endswith("Mechanics")),
    key=lambda value: value.__name__,
)


@cache
def parsed() -> tuple[tuple[Path, ast.Module], ...]:
    return tuple((path.resolve(), ast.parse(path.read_text())) for path in sorted(SOURCE.rglob("*.py")) if "alembic" not in path.parts)


def trees(skip: frozenset[Path]) -> list[ast.Module]:
    return [tree for path, tree in parsed() if path not in skip]


@cache
def called_attributes(skip: frozenset[Path]) -> set[str]:
    return {node.func.attr for tree in trees(skip) for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}


@cache
def read_attributes(skip: frozenset[Path]) -> set[str]:
    return {node.attr for tree in trees(skip) for node in ast.walk(tree) if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)}


def produced(kind: type[Enum]) -> set[str]:
    found: set[str] = set()
    roots = [(SOURCE / folder).resolve() for folder in PRODUCERS]
    for path, tree in parsed():
        if not any(root in path.parents for root in roots):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == kind.__name__:
                found.add(node.attr)
    return found


@pytest.mark.parametrize("mechanics", MECHANICS, ids=lambda value: value.__name__)
def test_every_effect_a_kind_of_the_heavens_gives_is_read_by_some_system(mechanics: type) -> None:
    used = called_attributes(frozenset({KINDS}))
    unread = [field.name for field in dataclasses.fields(mechanics) if field.name != "kind" and field.name not in used]
    assert unread == []


def test_every_pull_of_the_heavens_on_a_world_is_read_by_some_system() -> None:
    used = read_attributes(frozenset({PLACEMENT.resolve()}))
    assert [field.name for field in dataclasses.fields(CosmicPull) if field.name not in used] == []


@pytest.mark.parametrize("kind", [RiftCause, PhenomenonCause], ids=lambda value: value.__name__)
def test_every_cause_of_a_rift_or_phenomenon_is_one_the_engine_brings_about(kind: type[Enum]) -> None:
    assert sorted(member.name for member in kind if member.name not in produced(kind)) == []
