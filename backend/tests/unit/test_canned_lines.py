import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_canned_lines", REPOSITORY_ROOT / "scripts" / "check_canned_lines.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_canned_lines"] = module
    spec.loader.exec_module(module)
    return module


def test_a_pool_of_canned_sentences_is_caught() -> None:
    source = (
        "FATES = (\n"
        '    "That night the victim fled before dawn",\n'
        '    "A stranger died in the victim\'s place",\n'
        ")\n"
        'SIGNS = (Line("a.1", "one"), Line("a.2", "two"))\n'
        'LABELS = ("grain", "sacred goods")\n'
        "def tell(rng):\n"
        '    return rng.pick(("The sky split above the town", "The wells ran over at dawn"))\n'
    )
    assert [(item.line, item.name) for item in checker().pools({Path("lines.py"): source})] == [(1, "FATES"), (5, "SIGNS"), (8, "rng.pick")]


def test_no_source_keeps_a_pool_of_canned_sentences() -> None:
    module = checker()
    assert module.pools(module.sources()) == []
