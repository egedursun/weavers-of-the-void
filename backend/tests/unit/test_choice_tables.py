import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ENUMS = [frozenset({"fine", "flogging", "exile", "death", "public_shaming"})]


def wiring() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_wiring", REPOSITORY_ROOT / "scripts" / "check_wiring.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_wiring"] = module
    spec.loader.exec_module(module)
    return module


def test_a_choice_table_missing_an_enum_value_is_caught() -> None:
    module = wiring()
    partial = "export const PUNISHMENTS: Record<string, Named> = {\n  fine: x,\n  flogging: x,\n  exile: x,\n  death: x,\n}"
    used = "<ChoiceField table={PUNISHMENTS} />"
    assert module.label_gaps(partial, used, ENUMS) == [("PUNISHMENTS", ["public_shaming"])]
    whole = partial.replace("  death: x,\n}", "  death: x,\n  public_shaming: x,\n}")
    assert module.label_gaps(whole, used, ENUMS) == []
    assert module.label_gaps(partial, "named(PUNISHMENTS, value)", ENUMS) == []


def test_no_choice_table_in_the_app_misses_a_value() -> None:
    module = wiring()
    assert module.partial_choice_tables(module.frontend_text()) == []
