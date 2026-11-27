import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_auto_load", REPOSITORY_ROOT / "scripts" / "check_auto_load.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_auto_load"] = module
    spec.loader.exec_module(module)
    return module


def test_a_page_loader_with_its_own_observer_or_a_swapped_placeholder_is_caught() -> None:
    source = (
        "const { fetchNextPage } = pages\n"
        "const observer = new IntersectionObserver(() => load())\n"
        "{pages.isFetchingNextPage && <Skeleton className='h-24' />}"
    )
    assert len(checker().problems_in(source)) == 2


def test_every_page_loader_of_the_app_loads_steadily() -> None:
    module = checker()
    assert [path.name for path in module.sources() if module.problems_in(path.read_text(encoding="utf-8"))] == []
