import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
def mine(realm):
    return select(TreatyPartyRow.treaty_entity_id).where(TreatyPartyRow.party_node_id == realm.id)


def ours(realm_id):
    return select(TreatyPartyRow.treaty_entity_id).where(TreatyPartyRow.party_node_id == realm_id)


def kept(core):
    return select(TreatyPartyRow.treaty_entity_id).where(TreatyPartyRow.party_node_id == core)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_treaty_parties", REPOSITORY_ROOT / "scripts" / "check_treaty_parties.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_treaty_parties"] = module
    spec.loader.exec_module(module)
    return module


def test_a_realm_looked_for_among_treaty_parties_is_flagged() -> None:
    found = checker().raw_parties({Path("module.py"): RAW})
    assert [item.line for item in found] == [3, 7]


def test_the_backend_finds_a_realms_treaties_through_its_signatories() -> None:
    module = checker()
    assert module.raw_parties({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
