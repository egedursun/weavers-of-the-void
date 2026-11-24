import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_entry_categories", REPOSITORY_ROOT / "scripts" / "check_entry_categories.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_entry_categories"] = module
    spec.loader.exec_module(module)
    return module


def test_a_registry_line_and_a_category_key_are_read() -> None:
    module = checker()
    assert module.REGISTERED.findall("  'section-kin': 'life',\n") == [("section-kin", "life")]
    assert module.CATEGORY_KEY.findall("{ key: 'war', label: 'War' }") == ["war"]


def test_a_section_of_an_entry_page_without_an_id_is_caught(tmp_path: Path) -> None:
    module = checker()
    page = tmp_path / "Page.tsx"
    page.write_text("export function Page() {\n  return <Section title='Kin'>x</Section>\n}\n", encoding="utf-8")
    module.FRONTEND = tmp_path
    module.ENTRY_PAGES = page
    module.ROOT = tmp_path
    assert len(module.anonymous_sections()) == 1
    page.write_text("export function Page() {\n  return <Section id='section-kin' title='Kin'>x</Section>\n}\n", encoding="utf-8")
    assert module.anonymous_sections() == []


def test_every_section_of_the_app_lands_in_exactly_one_category() -> None:
    assert checker().problems() == []
