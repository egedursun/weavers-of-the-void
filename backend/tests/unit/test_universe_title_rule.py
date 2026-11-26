import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_universe_title", REPOSITORY_ROOT / "scripts" / "check_universe_title.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_universe_title"] = module
    spec.loader.exec_module(module)
    return module


def test_a_book_titled_by_the_first_world_is_caught() -> None:
    assert checker().misnamed("<h1>{{ book.title }}</h1>\n<title>{{ book.cosmos.name }}</title>\n") == [2]


def test_the_book_is_titled_by_the_universe() -> None:
    module = checker()
    assert [path.name for path in module.TITLED if module.misnamed(path.read_text(encoding="utf-8"))] == []
