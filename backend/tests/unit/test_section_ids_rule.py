import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_section_ids", REPOSITORY_ROOT / "scripts" / "check_section_ids.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_section_ids"] = module
    spec.loader.exec_module(module)
    return module


def test_a_section_id_and_a_family_section_are_both_read() -> None:
    module = checker()
    assert module.SECTION_ID.search("      id='section-kin'").group(1) == "section-kin"
    assert module.SECTION_ID.search("  section: 'section-kin',").group(1) == "section-kin"


def test_a_node_page_rendered_in_the_atlas_is_caught() -> None:
    module = checker()
    assert module.NODE_PAGES.search("  if (parsed.kind === 'entity') return <EntityView id={parsed.id} />")
    assert not module.NODE_PAGES.search("  return <AtlasHome records={records} kinds={kinds} onSelect={onSelect} />")


def test_no_two_sections_share_an_id_and_the_atlas_shows_no_node_page() -> None:
    assert checker().main() == 0
