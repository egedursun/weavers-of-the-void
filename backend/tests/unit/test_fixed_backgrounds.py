import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_fixed_backgrounds", REPOSITORY_ROOT / "scripts" / "check_fixed_backgrounds.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_fixed_backgrounds"] = module
    spec.loader.exec_module(module)
    return module


def test_a_background_pinned_to_the_viewport_is_caught() -> None:
    css = (
        "body {\n  background-color: red;\n  background-attachment: fixed;\n}\n"
        ".panel { background: url(a.webp) center / cover fixed; }\n"
        "@layer base { .card { @apply bg-fixed rounded; } }\n"
        ".calm { background-attachment: scroll; position: fixed; }\n"
    )
    assert checker().fixed_in_css(css) == ["body", ".panel", ".card"]


def test_a_fixed_background_in_markup_is_caught() -> None:
    code = (
        "const a = <div className='bg-fixed bg-cover' />\n"
        "const b = { backgroundAttachment: 'fixed' }\n"
        "const c = <div className='fixed inset-0 bg-fixed-ish' />\n"
    )
    assert checker().fixed_in_markup(code) == [1, 2]


def test_the_app_paints_no_background_pinned_to_the_viewport() -> None:
    assert checker().problems() == []


def test_a_folder_named_like_a_screen_is_not_read_as_one(tmp_path: Path) -> None:
    module = checker()
    (tmp_path / "__screenshots__" / "panel.test.tsx").mkdir(parents=True)
    (tmp_path / "panel.tsx").write_text("const a = <div className='bg-cover' />\n", encoding="utf-8")
    module.SOURCE_ROOT = tmp_path
    assert module.sources((".tsx",)) == [tmp_path / "panel.tsx"]
