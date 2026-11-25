import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_css_overrides", REPOSITORY_ROOT / "scripts" / "check_css_overrides.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_css_overrides"] = module
    spec.loader.exec_module(module)
    return module


def test_an_unlayered_class_that_overrides_a_utility_is_found(tmp_path: Path) -> None:
    styles = tmp_path / "styles"
    styles.mkdir()
    (styles / "panel.css").write_text(
        ".orb {\n  position: relative;\n  width: 3rem;\n}\n"
        ".orb::after {\n  position: absolute;\n}\n"
        ".halo::before {\n  position: absolute;\n}\n"
        "@layer components {\n  .chip {\n    display: flex;\n  }\n}\n"
        "@media (min-width: 40rem) {\n  .wide {\n    overflow: hidden;\n  }\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "Orb.tsx").write_text(
        "const a = cn('orb fixed z-40', tone)\nconst b = 'halo absolute'\nconst c = 'chip inline-flex'\n"
        "const d = 'wide md:overflow-auto'\nconst e = 'orb size-4'\n",
        encoding="utf-8",
    )
    found = checker().findings(tmp_path, styles)
    assert [(item.line, item.custom, item.utility) for item in found] == [(1, "orb", "fixed"), (4, "wide", "md:overflow-auto")]


def test_no_unlayered_class_overrides_a_utility_in_the_frontend() -> None:
    assert checker().findings() == []
