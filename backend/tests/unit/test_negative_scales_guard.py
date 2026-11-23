import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_negative_scales", REPOSITORY_ROOT / "scripts" / "check_negative_scales.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_negative_scales"] = module
    spec.loader.exec_module(module)
    return module


def test_a_bounded_scale_compared_below_zero_is_caught_and_input_checks_are_not() -> None:
    module = checker()
    source = "cold = land is not None and land.temperature < 0\nif request.temperature < 0:\n    raise ValueError\nwarm = land.temperature < 40\n"
    assert [(item.line, item.field) for item in module.belows({Path("engine/sample.py"): source}, module.floors())] == [(1, "temperature")]


def test_no_code_compares_a_scale_held_at_zero_or_above_below_zero() -> None:
    module = checker()
    assert module.belows(module.sources(), module.floors()) == []
