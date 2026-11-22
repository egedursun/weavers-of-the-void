import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_spec_duplicates.py"


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_spec_duplicates", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_value_added_twice_is_caught() -> None:
    check = checker()
    specs = {
        "16-minds-powers-living-craft.md": "`SoilKind` gains `laterite` and `permafrost`.",
        "17-w52-expansions.md": "`SoilKind` gains `gley` (waterlogged), `permafrost`; the rest stay.\n| D32 | `SoilKind` gains `laterite` again |",
    }
    assert [line.split(":")[0] for line in check.duplicates(specs)] == ["17-w52-expansions.md"]


def test_a_value_named_with_a_bias_word_is_caught() -> None:
    check = checker()
    found = check.biased({"17-w52-expansions.md": "`MaterialKind` gains `dragonbone` and `resin`."}, check.bias())
    assert len(found) == 1 and "dragonbone" in found[0]


def test_the_specs_add_no_value_twice() -> None:
    assert checker().main() == 0
