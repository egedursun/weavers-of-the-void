import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE = REPOSITORY_ROOT / "backend" / "src" / "aerona"


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_record_steps", REPOSITORY_ROOT / "scripts" / "check_record_steps.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_record_steps"] = module
    spec.loader.exec_module(module)
    return module


SAMPLE = """from aerona.domain.enums.records import StepAction as A
GOAL = "revival.goal_met"


async def met(ctx, people):
    await record(ctx, GOAL, roles={}, steps=(StepDraft(A.SETTLE, actor=people.id),))


async def chosen(ctx, people):
    steps = [StepDraft(A.SETTLE, actor=people.id)]
    steps.append(StepDraft(A.LEAVE, actor=people.id))
    await record(ctx, "revival.way_chosen", roles={}, steps=steps)


async def quiet(ctx, people):
    await record(ctx, "revival.way_chosen", roles={}, steps=(StepDraft(A.SETTLE),))
"""


def test_a_step_the_kind_does_not_declare_is_caught_through_constants_and_names() -> None:
    declared = {"revival.goal_met": frozenset(), "revival.way_chosen": frozenset({"settle"})}
    found = checker().strays({SOURCE / "engine" / "sample.py": SAMPLE}, declared)
    assert [(item.key, item.action) for item in found] == [("revival.goal_met", "settle"), ("revival.way_chosen", "leave")]


PLACED = """from aerona.engine.recording.record import record as record_incident


async def founded(ctx, faction, home):
    await record_incident(ctx, "movement.founded", roles={})


async def kept(ctx, faction, home):
    await record_incident(ctx, "movement.founded", roles={}, place=home.id)


async def told(ctx, faction):
    await record_incident(ctx, "movement.rose", roles={})
"""


def test_a_kind_that_needs_its_place_recorded_without_one_is_caught_through_an_alias() -> None:
    found = checker().placeless({SOURCE / "engine" / "sample.py": PLACED}, frozenset({"movement.founded"}))
    assert [(item.key, item.line) for item in found] == [("movement.founded", 5)]


def test_no_happening_is_recorded_with_a_step_its_kind_does_not_declare_or_without_the_place_it_needs() -> None:
    module = checker()
    code = module.sources()
    assert module.strays(code, module.declared_steps()) == []
    assert module.placeless(code, module.placed_kinds()) == []
