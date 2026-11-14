import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_theme_tokens", REPOSITORY_ROOT / "scripts" / "check_theme_tokens.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_theme_tokens"] = module
    spec.loader.exec_module(module)
    return module


def test_a_theme_token_missing_from_class_merging_is_caught() -> None:
    theme = "--spacing-portrait-xl: 8rem;\n--spacing-portrait-2xl: 9rem;\n--text-title: 2rem;\n--text-title--line-height: 1.2;\n"
    utils = "export const TEXT_ROLES = ['title']\nexport const SPACING_TOKENS = [\n  'portrait-xl',\n]\n"
    assert checker().gaps(theme, utils) == ["--spacing-portrait-2xl is in the theme but not in SPACING_TOKENS"]


def test_class_merging_knows_every_theme_token() -> None:
    module = checker()
    assert module.gaps(module.THEME.read_text(encoding="utf-8"), module.UTILS.read_text(encoding="utf-8")) == []
