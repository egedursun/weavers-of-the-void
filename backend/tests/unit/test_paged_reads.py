import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_paged_reads", REPOSITORY_ROOT / "scripts" / "check_paged_reads.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_paged_reads"] = module
    spec.loader.exec_module(module)
    return module


def test_a_page_cut_from_a_list_built_again_for_every_page_is_caught() -> None:
    rebuilt = "full = await graph(session)\nreturn full.nodes[node_offset : node_offset + node_limit]"
    kept = "full = await per_state(database, KEY, built)\nreturn full.nodes[node_offset : node_offset + node_limit]"
    assert checker().rebuilt_pages(rebuilt) and not checker().rebuilt_pages(kept)


def test_every_paged_read_of_the_api_builds_its_list_once_per_world_state() -> None:
    module = checker()
    assert [name for path in sorted(module.ROUTERS.glob("*.py")) for name, source, _line in module.handlers(path) if module.rebuilt_pages(source)] == []
