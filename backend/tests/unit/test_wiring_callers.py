import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_wiring", REPOSITORY_ROOT / "scripts" / "check_wiring.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_wiring"] = module
    spec.loader.exec_module(module)
    return module


def test_a_lever_named_only_in_a_type_listing_has_no_caller() -> None:
    module = checker()
    listed = "export type Action =\n  | 'ward:set'\n  | 'ward:edit'\n"
    called = listed + "useAction('ward:set', (_: void) => ({}))\n"
    assert "ward:edit" not in module.calling_text(listed)
    assert "ward:set" in module.calling_text(called) and "ward:edit" not in module.calling_text(called)
