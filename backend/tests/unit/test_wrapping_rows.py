import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_wrapping_rows", REPOSITORY_ROOT / "scripts" / "check_wrapping_rows.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_wrapping_rows"] = module
    spec.loader.exec_module(module)
    return module


def test_a_wrapping_row_that_may_not_shrink_is_caught() -> None:
    source = "<div className='flex shrink-0 flex-wrap gap-1'>\n<div className=\"flex min-w-0 flex-wrap\">\n<span className={`flex-none flex-wrap ${x}`}>"
    assert checker().rigid_rows(source) == [1, 3]


def test_every_wrapping_row_of_the_app_may_shrink() -> None:
    module = checker()
    assert [path.name for path in module.sources() if module.rigid_rows(path.read_text(encoding="utf-8"))] == []
