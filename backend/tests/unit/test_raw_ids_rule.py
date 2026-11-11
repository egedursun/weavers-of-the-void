import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_raw_ids", REPOSITORY_ROOT / "scripts" / "check_raw_ids.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_raw_ids"] = module
    spec.loader.exec_module(module)
    return module


def test_a_record_shown_by_its_raw_number_is_caught_but_search_words_are_not() -> None:
    module = checker()
    shown = "['Event', row.collection_id !== null ? `#${row.collection_id}` : 'none'],"
    text = "\n".join([shown, "keywords: `#${item.parent_id} x`,", "['Event', row.collection_name ?? 'none'],"])
    assert module.raw_ids_in(text) == [1]
