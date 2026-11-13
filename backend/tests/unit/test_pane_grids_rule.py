import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_pane_grids", REPOSITORY_ROOT / "scripts" / "check_pane_grids.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_pane_grids"] = module
    spec.loader.exec_module(module)
    return module


def test_a_pane_grid_split_by_the_screen_is_caught_but_one_split_by_its_container_is_not() -> None:
    module = checker()
    text = "\n".join(
        [
            "<dl className='grid grid-cols-1 sm:grid-cols-2'>",
            "<dl className='grid grid-cols-1 @md/facts:grid-cols-2'>",
            "<div className={cn('flex', long && 'lg:col-span-2')}>",
            "<div className='@sm:grid-cols-3 gap-2'>",
        ]
    )
    assert module.viewport_grids_in(text) == [1, 3]


def test_every_pane_lays_its_grids_out_by_its_container() -> None:
    module = checker()
    assert module.pane_files()
    assert module.main() == 0
