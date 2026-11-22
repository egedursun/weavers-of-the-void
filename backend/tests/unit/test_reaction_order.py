import ast
import inspect
import re
import textwrap
from collections.abc import Callable
from typing import Any

from aerona.engine.interconnect.catalog_orders51 import ORDERS51_MECHANICS
from aerona.engine.phase import Phase
from aerona.engine.pipeline import PRE_TRANSITION_ORDER, TICK_ORDER, TRANSITION_ORDER

ONE_EPOCH = TICK_ORDER + PRE_TRANSITION_ORDER + TRANSITION_ORDER
READ = re.compile(r"\b(\w+Row)\.((?!until|expires|due)\w*epoch)\s*(?:==|>=)\s*ctx\.epoch(?!\s*[-+])")
DEPTH = 6
REACTIONS = frozenset(mechanic.key for mechanic in ORDERS51_MECHANICS)


def body(function: Callable[..., Any]) -> str:
    try:
        return textwrap.dedent(inspect.getsource(function))
    except (OSError, TypeError):
        return ""


def callees(function: Callable[..., Any]) -> list[Callable[..., Any]]:
    module = inspect.getmodule(function)
    found: list[Callable[..., Any]] = []
    for node in ast.walk(ast.parse(body(function) or "pass")):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            named = getattr(module, node.func.id, None)
            target = inspect.unwrap(named) if callable(named) else None
            if inspect.isfunction(target) and target.__module__.startswith("aerona.engine"):
                found.append(target)
    return found


def reached(phase: Phase) -> list[str]:
    seen: set[Callable[..., Any]] = set()
    stack: list[tuple[Callable[..., Any], int]] = [(inspect.unwrap(phase.run), 0)]
    while stack:
        function, depth = stack.pop()
        if function in seen:
            continue
        seen.add(function)
        if depth < DEPTH:
            stack.extend((callee, depth + 1) for callee in callees(function))
    return [body(function) for function in seen]


def writes(text: str, row: str, column: str) -> bool:
    if not re.search(rf"\b{row}\b", text):
        return False
    return bool(re.search(rf"\.{column}\s*=[^=]", text) or re.search(rf"\b{row}\((?:[^()]|\([^()]*\))*\b{column}=", text, re.S))


def late_reads(phases: tuple[Phase, ...], reactions: frozenset[str]) -> list[str]:
    texts = [reached(phase) for phase in phases]
    found: set[str] = set()
    for position, phase in enumerate(phases):
        if phase.name not in reactions:
            continue
        for text in texts[position]:
            for hit in READ.finditer(text):
                row, column = hit.group(1), hit.group(2)
                if row.startswith("Incident"):
                    continue
                later = sorted({phases[index].name for index in range(position + 1, len(phases)) if any(writes(other, row, column) for other in texts[index])})
                if later:
                    found.add(f"{phase.name} reads {row}.{column} of this epoch before {', '.join(later)} writes it")
    return sorted(found)


def test_every_mechanic_that_reacts_to_this_epoch_runs_after_what_it_reacts_to() -> None:
    assert late_reads(ONE_EPOCH, REACTIONS) == []


def test_a_reaction_placed_before_its_cause_is_caught() -> None:
    honours = next(phase for phase in ONE_EPOCH if phase.name == "person_honours")
    contests = next(phase for phase in ONE_EPOCH if phase.name == "relations_contests")
    assert late_reads((honours, contests), frozenset({"person_honours"})) == [
        "person_honours reads DeedRow.epoch of this epoch before relations_contests writes it"
    ]
