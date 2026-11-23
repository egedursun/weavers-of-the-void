import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
def frozen(land):
    return land.temperature < 0


def scorched(land):
    return land.temperature > 120


def sensible(land):
    return land.temperature <= 0 or land.temperature >= 100 or land.temperature < 30 or land.temperature_band is None
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_temperature_scale", REPOSITORY_ROOT / "scripts" / "check_temperature_scale.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_temperature_scale"] = module
    spec.loader.exec_module(module)
    return module


def test_a_temperature_read_outside_its_scale_is_flagged() -> None:
    assert [item.line for item in checker().readings({Path("module.py"): SOURCE})] == [3, 7]


def test_the_backend_never_compares_a_temperature_outside_its_scale() -> None:
    module = checker()
    assert module.readings({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
