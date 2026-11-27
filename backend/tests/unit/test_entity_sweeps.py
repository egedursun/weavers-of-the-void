import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_entity_sweeps", REPOSITORY_ROOT / "scripts" / "check_entity_sweeps.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_entity_sweeps"] = module
    spec.loader.exec_module(module)
    return module


def test_a_screen_that_sweeps_every_record_to_keep_a_few_kinds_is_caught() -> None:
    swept = "const entities = useAllEntities(CANON, true)\nconst towns = ranked(entities.data ?? [], 'settlement', world)"
    asked = "const towns = useEntitiesOfType(CANON, 'settlement', true)\nconst ranked = ranked(towns.data ?? [], 'settlement', world)"
    assert checker().picks_types_from_a_sweep(swept) and not checker().picks_types_from_a_sweep(asked)


def test_no_screen_sweeps_every_record_to_keep_a_few_kinds() -> None:
    module = checker()
    assert [path.name for path in module.sources() if module.picks_types_from_a_sweep(path.read_text(encoding="utf-8"))] == []
