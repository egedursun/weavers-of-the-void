import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_root_overflow", REPOSITORY_ROOT / "scripts" / "check_root_overflow.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_root_overflow"] = module
    spec.loader.exec_module(module)
    return module


def test_an_overflow_on_the_root_element_is_caught() -> None:
    css = "@layer base {\n  html {\n    @apply overflow-x-hidden;\n  }\n  :root.dark { overflow-y: clip; }\n  body { overflow-x: hidden; }\n}\n"
    assert checker().clipped_roots(css) == ["html", ":root.dark"]


def test_the_app_keeps_the_root_element_free_of_overflow() -> None:
    module = checker()
    assert [path.name for path in module.stylesheets() if module.clipped_roots(path.read_text(encoding="utf-8"))] == []
