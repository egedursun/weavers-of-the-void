import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
def enemy(item, realm):
    return item.defender_id if item.attacker_id == realm else item.attacker_id


def foes(wars, realm):
    return {side for war in wars for side in war.sides if side != realm}


def kept(item):
    return item.foe_id
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_war_foes", REPOSITORY_ROOT / "scripts" / "check_war_foes.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_war_foes"] = module
    spec.loader.exec_module(module)
    return module


def test_a_foe_found_by_comparing_a_raw_side_is_flagged() -> None:
    found = checker().raw_foes({Path("module.py"): RAW})
    assert [item.line for item in found] == [3, 7]


def test_the_backend_finds_foes_only_through_the_war_service() -> None:
    module = checker()
    assert module.raw_foes({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
