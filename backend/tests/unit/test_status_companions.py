import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import CheckConstraint

import aerona.db.tables
from aerona.db.base import Base

TABLES = aerona.db.tables
SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
STOPS = (ast.Return, ast.Raise, ast.Continue, ast.Break)


@dataclass(frozen=True)
class Pairing:
    enum: str
    companions: frozenset[str]
    ended: frozenset[str]
    open_only: frozenset[str]

    def ends(self, value: ast.expr) -> bool:
        if isinstance(value, ast.IfExp):
            return self.ends(value.body) or self.ends(value.orelse)
        if not (isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id[0].isupper()):
            return True
        if value.value.id != self.enum:
            return False
        member = value.attr.lower()
        return member in self.ended if self.ended else member not in self.open_only


def pairings() -> list[Pairing]:
    found: list[Pairing] = []
    for table in Base.metadata.tables.values():
        column = table.c.get("status")
        enum = getattr(getattr(column, "type", None), "enum_class", None)
        for constraint in table.constraints:
            text = str(constraint.sqltext) if isinstance(constraint, CheckConstraint) else ""
            companions = frozenset(re.findall(r"(\w+) IS NOT NULL", text))
            if enum is None or not re.match(r"status\b", text) or not companions:
                continue
            quoted = frozenset(re.findall(r"'(\w+)'", text.split(" OR ")[0]))
            opens = bool(re.match(r"status = '", text))
            found.append(Pairing(enum.__name__, companions, frozenset() if opens else quoted, quoted if opens else frozenset()))
    return found


def blocks_of(node: ast.AST) -> Iterator[list[ast.stmt]]:
    for field in ("body", "orelse", "finalbody", "handlers", "cases"):
        block = getattr(node, field, None)
        if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
            yield block
        elif isinstance(block, list):
            for part in block:
                yield from blocks_of(part)


def paths_to(fn: ast.AsyncFunctionDef) -> dict[int, list[tuple[list[ast.stmt], int]]]:
    found: dict[int, list[tuple[list[ast.stmt], int]]] = {}

    def visit(block: list[ast.stmt], trail: list[tuple[list[ast.stmt], int]]) -> None:
        for index, stmt in enumerate(block):
            here = [*trail, (block, index)]
            found[id(stmt)] = here
            if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                continue
            for inner in blocks_of(stmt):
                visit(inner, here)

    visit(fn.body, [])
    return found


def events(stmt: ast.stmt) -> list[tuple[int, int, str, str]]:
    found: list[tuple[int, int, str, str]] = []
    for node in ast.walk(stmt):
        if isinstance(node, ast.Await):
            found.append((node.lineno, node.col_offset, "await", ""))
        if isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute):
                    found.append((node.end_lineno or node.lineno, node.end_col_offset or 0, target.attr, ast.unparse(target.value)))
    return sorted(found)


def awaited_before_companion(trail: list[tuple[list[ast.stmt], int]], owner: str, companions: frozenset[str]) -> bool:
    awaited = False
    for block, index in reversed(trail):
        for stmt in block[index + 1 :]:
            for _, _, kind, whose in events(stmt):
                awaited = awaited or kind == "await"
                if kind in companions and whose == owner:
                    return awaited
            if isinstance(stmt, STOPS):
                return False
    return False


def status_writes(fn: ast.AsyncFunctionDef) -> Iterator[tuple[ast.Assign, ast.Attribute]]:
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "status":
                    yield node, target


def set_before(fn: ast.AsyncFunctionDef, write: ast.Assign, owner: str, companions: frozenset[str]) -> bool:
    return any(
        isinstance(node, ast.Assign)
        and node.lineno < write.lineno
        and any(isinstance(target, ast.Attribute) and target.attr in companions and ast.unparse(target.value) == owner for target in node.targets)
        for node in ast.walk(fn)
    )


def half_ended_writes(text: str, rules: list[Pairing]) -> list[str]:
    found: list[str] = []
    for fn in ast.walk(ast.parse(text)):
        if not isinstance(fn, ast.AsyncFunctionDef):
            continue
        trails = paths_to(fn)
        for node, target in status_writes(fn):
            companions = frozenset().union(*(rule.companions for rule in rules if rule.ends(node.value)))
            owner = ast.unparse(target.value)
            trail = trails.get(id(node))
            if companions and trail and not set_before(fn, node, owner, companions) and awaited_before_companion(trail, owner, companions):
                found.append(f"{node.lineno}: {owner}.status is set before an await that comes ahead of {sorted(companions)}")
    return found


def test_an_ended_status_is_never_left_without_its_epoch_across_an_await() -> None:
    rules = pairings()
    found = [f"{path.relative_to(SOURCE)}:{line}" for path in sorted(SOURCE.rglob("*.py")) for line in half_ended_writes(path.read_text(), rules)]
    assert not found, found


def test_the_guard_catches_a_death_whose_epoch_waits_on_a_query() -> None:
    rules = pairings()
    late = (
        "async def mark(session, entity, status):\n"
        "    entity.status = status\n"
        "    if status is EntityStatus.DEAD:\n"
        "        cosmos = await read(session)\n"
        "        entity.end_epoch = cosmos.epoch\n"
    )
    early = (
        "async def mark(session, entity, status):\n"
        "    if status is EntityStatus.DEAD:\n"
        "        cosmos = await read(session)\n"
        "        entity.end_epoch = cosmos.epoch\n"
        "    entity.status = status\n"
    )
    waiting = "async def wait(journey):\n    journey.status = JourneyStatus.UNDERWAY\n    await step(journey)\n    journey.end_epoch = 3\n"
    settled = "async def settle(row, status):\n    row.status = status\n    await flush(row)\n"
    assert half_ended_writes(late, rules)
    assert not half_ended_writes(early, rules)
    assert not half_ended_writes(waiting, rules)
    assert not half_ended_writes(settled, rules)
